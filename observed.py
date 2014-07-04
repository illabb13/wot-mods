# coding=utf-8

__author__ = "illabb13"
__copyright__ = "Copyright 2014, illabb13"
__version__ = '1.0 (WoT 0.9.1)'
__email__ = "illabb13@gmail.com"

import BigWorld
import ResMgr
import Keys
from Avatar import PlayerAvatar
from constants import VEHICLE_MISC_STATUS
from gui.WindowsManager import g_windowsManager
from constants import ARENA_GUI_TYPE, PREBATTLE_TYPE
from gui.Scaleform.Minimap import Minimap
from math import trunc
from messenger.proto.bw.battle_chat_cmd import SendChatCommandDecorator
from chat_shared import CHAT_COMMANDS
from gui.BattleContext import g_battleContext
from messenger import MessengerEntry
from messenger.proto.bw.find_criteria import BWPrbChannelFindCriteria, BWBattleTeamChannelFindCriteria


class ObservedMod(object):
    # params in camel-case style for compatibility with xml
    # default values
    disabledByStartBattle = 1
    limitationTypeOfBattles = 1
    enabledForVehType = ['HeavyTank', 'MediumTank', 'LightTank', 'AT-SPG', 'SPG']
    showWhenLess = 0
    showWhenLessInRandom = 4
    message = 'Меня засветили на квадрате {cell}!'
    useSquadChat = 0
    helpMeOption = 0
    cellClickOption = 0
    timeEndMessage = 10
    endMessage = 'Прошло {time} секунд. Возможно ты уже не в засвете. Вперед за дамажкой!'
    hotKey = [Keys.KEY_F10]

    # enabled flags
    isEnabled = True  # not changed during the battle
    isTurnedOn = True  # changed

    # custom values
    endMessageCID = None
    isUseCellVar = None

    def __init__(self, params=None):
        if params is not None:
            for k, v in params:
                setattr(self, k, v)

        self.initialize()

    def is_mod_enabled(self):
        return self.isEnabled and self.isTurnedOn

    @staticmethod
    def show_player_panel_message(message, color='purple'):
        if g_windowsManager.battleWindow is not None:
            func_name = 'battle.PlayerMessagesPanel.ShowMessage'
            g_windowsManager.battleWindow.proxy.call(func_name, ['observed', message, color])

    def show_observed_end_message(self):
        self.endMessageCID = None
        message = self.endMessage.format(time=self.timeEndMessage)
        self.show_player_panel_message(message)

    @staticmethod
    def get_cell_index(position, bb):
        map_size = Minimap._Minimap__MINIMAP_CELLS[1]
        bl, tr = bb
        arena_x, arena_z = tr.x - bl.x, tr.y - bl.y
        real_pos_x, real_pos_z = position.x - bl.x, position.z - bl.y
        column = trunc(real_pos_x / arena_x * map_size)
        row = trunc((arena_z - real_pos_z) / arena_z * map_size)
        return column * map_size + row

    @staticmethod
    def analyze_hotKey_param(value, default):
        keys = map(lambda key: key if key.startswith('KEY_') else 'KEY_' + key, value.split('+'))
        key_codes = filter(lambda code: code is not None, map(lambda key: getattr(Keys, key, None), keys))

        if len(keys) != len(key_codes):
            return default

        return key_codes

    @staticmethod
    def analyze_enabledForVehType_param(value, default):
        types = filter(lambda vt: vt in default, map(lambda vt: vt.strip(), value.split(',')))

        if not len(types):
            return default

        return types

    def initialize(self):
        try:
            config_file = ResMgr.openSection('scripts/client/mods/observed.xml')

            for name, value in config_file.items():
                if not hasattr(self, name):
                    continue

                default_value = getattr(self, name)
                current = value.asInt if type(default_value) is int else value.asString

                if name == 'hotKey':
                    current = self.analyze_hotKey_param(current, default_value)
                elif name == 'enabledForVehType':
                    current = self.analyze_enabledForVehType_param(current, default_value)

                setattr(self, name, current)
        except Exception, e:
            print 'OBSERVED MOD READ PARAMS ERROR: %s' % e

        self.isEnabled = True
        self.isTurnedOn = not self.disabledByStartBattle

        self.endMessageCID = None
        self.isUseCellVar = '{cell}' in self.message or self.cellClickOption


# ======================================================================================================================
# functions, classes and global variables
# ======================================================================================================================
# TODO: function for init this methods
orig_onEnterWorld = PlayerAvatar.onEnterWorld
orig_updateVehicleMiscStatus = PlayerAvatar.updateVehicleMiscStatus
orig_handleKey = PlayerAvatar.handleKey

om = ObservedMod()


def custom_onEnterWorld(self, prereqs):
    orig_onEnterWorld(self, prereqs)

    om.initialize()

    gui_type = self.arena.guiType
    is_random = gui_type == ARENA_GUI_TYPE.RANDOM

    om.isEnabled = True
    om.isTurnedOn = not om.disabledByStartBattle
    om.useSquadChat = om.useSquadChat and is_random

    if om.limitationTypeOfBattles and gui_type not in (ARENA_GUI_TYPE.UNKNOWN, ARENA_GUI_TYPE.TRAINING, ARENA_GUI_TYPE.COMPANY, ARENA_GUI_TYPE.CYBERSPORT):
        om.isEnabled = False

    if len(om.enabledForVehType) != 5:
        tags = self.vehicleTypeDescriptor.type.tags
        if not any(veh_type in tags for veh_type in om.enabledForVehType):
            om.isEnabled = False

    if is_random:
        om.showWhenLess = om.showWhenLessInRandom


def custom_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg):
    orig_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg)

    if om.is_mod_enabled() and code == VEHICLE_MISC_STATUS.IS_OBSERVED_BY_ENEMY:
        alive_allies = {id: data for id, data in self.arena.vehicles.items() if data['team'] == self.team and data['isAlive']}
        alive_count = len(alive_allies)

        if om.useSquadChat:
            om.useSquadChat = sum([g_battleContext.isSquadMan(vID=v_id) for v_id in alive_allies.keys()]) > 1

        if om.showWhenLess and alive_count > om.showWhenLess and not om.useSquadChat:
            return

        minimap = g_windowsManager.battleWindow.minimap
        cell = om.get_cell_index(self.position, self.arena.arenaType.boundingBox) if om.isUseCellVar else 0

        if om.message:
            message = om.message
            if '{cell}' in message:
                message = message.format(cell=minimap.getCellName(cell))

            controls = MessengerEntry.g_instance.gui.channelsCtrl
            criteria = BWPrbChannelFindCriteria(PREBATTLE_TYPE.SQUAD) if om.useSquadChat else BWBattleTeamChannelFindCriteria()
            controller = controls.getControllerByCriteria(criteria)
            if controller:
                controller.sendMessage(message)

        more_than_one = alive_count > 1

        if om.helpMeOption and not om.useSquadChat and more_than_one:
            g_windowsManager.battleWindow.chatCommands.sendCommand('HELPME')

        if om.cellClickOption and not om.useSquadChat and more_than_one:
            decorator = SendChatCommandDecorator(CHAT_COMMANDS.ATTENTIONTOCELL, second=cell)
            g_windowsManager.battleWindow.chatCommands._ChatCommandsController__sendChatCommand(decorator)

        if om.timeEndMessage:
            if om.endMessageCID is not None:
                BigWorld.cancelCallback(om.endMessageCID)
            om.endMessageCID = BigWorld.callback(om.timeEndMessage, om.show_observed_end_message)


def custom_handleKey(self, isDown, key, mods):
    orig_handleKey(self, isDown, key, mods)

    if len(om.hotKey) == 1:
        is_needle_keys = key == om.hotKey[0]
    elif len(om.hotKey) == 2:
        is_needle_keys = key == om.hotKey[1] and BigWorld.isKeyDown(om.hotKey[0])
    else:
        is_needle_keys = False

    if is_needle_keys and isDown:
        om.isTurnedOn = not om.isTurnedOn
        om.show_player_panel_message('Observed Mod %s' % ('ВКЛЮЧЕН' if om.isTurnedOn else 'ОТКЛЮЧЕН'))


PlayerAvatar.onEnterWorld = custom_onEnterWorld
PlayerAvatar.updateVehicleMiscStatus = custom_updateVehicleMiscStatus
PlayerAvatar.handleKey = custom_handleKey