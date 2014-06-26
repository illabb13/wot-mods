# coding=utf-8

__author__ = "illabb13"
__copyright__ = "Copyright 2014, illabb13"
__version__ = '0.9 (WoT 0.9.1)'
__email__ = "illabb13@gmail.com"

import BigWorld
import ResMgr
import Keys
from Avatar import PlayerAvatar
from constants import VEHICLE_MISC_STATUS
from ChatManager import chatManager
from gui.WindowsManager import g_windowsManager
from constants import ARENA_GUI_TYPE
from gui.Scaleform.Minimap import Minimap
import math
from messenger.proto.bw.battle_chat_cmd import SendChatCommandDecorator
from chat_shared import CHAT_COMMANDS


def analyze_hotKey_param(value, default):
    keys = map(lambda key: key if key.startswith('KEY_') else 'KEY_' + key, value.split('+'))
    key_codes = filter(lambda code: code is not None, map(lambda key: getattr(Keys, key, None), keys))

    if len(keys) != len(key_codes):
        return default

    return key_codes


def analyze_enabledForVehType_param(value, default):
    types = filter(lambda vt: vt in default, map(lambda vt: vt.strip(), value.split(',')))

    if not len(types):
        return default

    return types

# ======================================================================================================================
# дефолтные настройки
params = {
    'isEnabled': 0,  # кандидат на удаление
    'disabledByStartBattle': 1,
    'limitationTypeOfBattles': 1,
    'enabledForVehType': ['LightTank', 'MediumTank', 'HeavyTank', 'SPG', 'AT-SPG'],
    'showWhenLess': 0,
    'message': 'Меня засветили на квадрате {cell}!',
    'helpMeOption': 0,
    'cellClickOption': 0,
    'timeEndMessage': 10,
    'endMessage': 'Прошло {time} секунд. Возможно ты уже не в засвете. Вперед за дамажкой!',
    'enableHotKey': 1,
    'hotKey': [Keys.KEY_F10]
}

try:
    config_file = ResMgr.openSection('scripts/client/mods/observed.xml')

    for name, value in config_file.items():
        if name not in params:
            continue

        current = value.asInt if type(params[name]) is int else value.asString

        if name == 'hotKey':
            current = analyze_hotKey_param(current, params[name])
        elif name == 'enabledForVehType':
            current = analyze_enabledForVehType_param(current, params[name])

        params[name] = current
except Exception, e:
    print 'OBSERVED MOD ERROR: %s' % e


# ======================================================================================================================
def show_player_panel_message(message, color='purple'):
    if g_windowsManager.battleWindow is not None:
        func_name = 'battle.PlayerMessagesPanel.ShowMessage'
        g_windowsManager.battleWindow.proxy.call(func_name, ['observed', message, color])


def show_observed_end_message():
    message = params['endMessage'].format(time=params['timeEndMessage'])
    show_player_panel_message(message)

# ======================================================================================================================
# TODO: сделать функцию для добавления своего обработчика
orig_onEnterWorld = PlayerAvatar.onEnterWorld
orig_updateVehicleMiscStatus = PlayerAvatar.updateVehicleMiscStatus
orig_handleKey = PlayerAvatar.handleKey

is_needle_battles_type = (
    ARENA_GUI_TYPE.UNKNOWN,  # Специальный бой
    ARENA_GUI_TYPE.TRAINING,  # Тренировочный бой
    ARENA_GUI_TYPE.COMPANY,  # Ротный бой
    ARENA_GUI_TYPE.CYBERSPORT  # Командный бой
)

# кастомные функции
def custom_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg):
    orig_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg)

    if params['isEnabled'] and code == VEHICLE_MISC_STATUS.IS_OBSERVED_BY_ENEMY:
        if params['limitationTypeOfBattles'] and self.arena.guiType not in is_needle_battles_type:
            return

        if len(params['enabledForVehType']) != 5:
            tags = self.vehicleTypeDescriptor.type.tags
            if not any(veh_type in tags for veh_type in params['enabledForVehType']):
                return

        if params['showWhenLess']:
            vehicles_data = self.arena.vehicles.values()
            alive_count = sum([data['isAlive'] and data['team'] == self.team for data in vehicles_data])
            if alive_count > params['showWhenLess']:
                return

        team_channel_id = chatManager.battleTeamChannelID
        minimap = g_windowsManager.battleWindow.minimap

        # TODO: сделать функцию и вызывать при необходимости
        map_size = Minimap._Minimap__MINIMAP_CELLS[1]
        position = self.position
        bl, tr = self.arena.arenaType.boundingBox
        arena_x, arena_z = tr.x - bl.x, tr.y - bl.y
        real_pos_x, real_pos_z = position.x - bl.x, position.z - bl.y
        column = math.trunc(real_pos_x / arena_x * map_size)
        row = math.trunc((arena_z - real_pos_z) / arena_z * map_size)
        cell = column * map_size + row

        message = params['message']
        if '{cell}' in message:
            message = message.format(cell=minimap.getCellName(cell))

        if message:
            self.broadcast(team_channel_id, message)

        if params['helpMeOption']:
            # CHAT_COMMANDS?
            self.broadcast(team_channel_id, '/HELPME')

        if params['cellClickOption']:
            decorator = SendChatCommandDecorator(CHAT_COMMANDS.ATTENTIONTOCELL, second=cell)
            minimap._Minimap__parentUI.chatCommands._ChatCommandsController__sendChatCommand(decorator)

        if params['timeEndMessage']:
            BigWorld.callback(params['timeEndMessage'], show_observed_end_message)


def custom_handleKey(self, isDown, key, mods):
    orig_handleKey(self, isDown, key, mods)

    is_needle_keys = False

    if len(params['hotKey']) == 1:
        is_needle_keys = key == params['hotKey'][0]
    elif len(params['hotKey']) == 2:
        is_needle_keys = key == params['hotKey'][1] and BigWorld.isKeyDown(params['hotKey'][0])

    if is_needle_keys and isDown:
        params['isEnabled'] = not params['isEnabled']
        show_player_panel_message('Observed Mod %s' % ('ВКЛЮЧЕН' if params['isEnabled'] else 'ОТКЛЮЧЕН'))


def custom_onEnterWorld(self, prereqs):
    orig_onEnterWorld(self, prereqs)

    params['isEnabled'] = not params['disabledByStartBattle']

# ======================================================================================================================
# основная часть
PlayerAvatar.onEnterWorld = custom_onEnterWorld
PlayerAvatar.updateVehicleMiscStatus = custom_updateVehicleMiscStatus
if params['enableHotKey']:
    PlayerAvatar.handleKey = custom_handleKey