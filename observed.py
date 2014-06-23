# coding=utf-8

__author__ = "illabb13"
__copyright__ = "Copyright 2014, illabb13"
__version__ = '0.8 (WoT 0.9.1)'
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

# ======================================================================================================================
# дефолтные настройки
params = {
    'isEnabled': 0,  # кандидат на удаление
    'disabledByStartBattle': 1,
    'showWhenLess': 6,
    'limitationTypeOfBattles': 1,
    'message': 'Меня засветили, япона мать! :)',
    'helpMeOption': 2,
    'cellClickOption': 2,
    'timeEndMessage': 10,
    'endMessage': 'Прошло {time} секунд. Возможно ты уже не в засвете. Вперед за дамажкой!',
    'enableHotKey': 1
}

try:
    config_file = ResMgr.openSection('scripts/client/mods/observed.xml')

    for name, value in config_file.items():
        if name not in params:
            continue
        params[name] = value.asInt if type(params[name]) is int else value.asString
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
    ARENA_GUI_TYPE.UNKNOWN,    # Специальный бой
    ARENA_GUI_TYPE.TRAINING,   # Тренировочный бой
    ARENA_GUI_TYPE.COMPANY,    # Ротный бой
    ARENA_GUI_TYPE.CYBERSPORT  # Командный бой
)

map_size = Minimap._Minimap__MINIMAP_CELLS[1]

# кастомные функции
def custom_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg):
    orig_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg)

    if params['isEnabled'] and code == VEHICLE_MISC_STATUS.IS_OBSERVED_BY_ENEMY:
        if params['limitationTypeOfBattles'] and self.arena.guiType not in is_needle_battles_type:
            return
        
        if params['showWhenLess']:
            vehicles = self.arena.vehicles
            alive_count = 0
            for data in vehicles.values():
                if data['isAlive'] and data['team'] == self.team:
                    alive_count += 1
            if alive_count > params['showWhenLess']:
                return

        team_channel_id = chatManager.battleTeamChannelID
        minimap = g_windowsManager.battleWindow.minimap
        self.broadcast(team_channel_id, params['message'])

        if params['helpMeOption']:
            # import CHAT_COMMANDS?
            self.broadcast(team_channel_id, '/HELPME')

        if params['cellClickOption']:
            position = self.position
            bl, tr = self.arena.arenaType.boundingBox
            arena_x, arena_z = tr.x - bl.x, tr.y - bl.y
            real_pos_x, real_pos_z = position.x - bl.x, position.z - bl.y
            column = math.trunc(real_pos_x / arena_x * map_size)
            row = math.trunc((arena_z - real_pos_z) / arena_z * map_size)
            cell = column * map_size + row
            # minimap._Minimap__parentUI.chatCommands.sendAttentionToCell(cell)
            decorator = SendChatCommandDecorator(CHAT_COMMANDS.ATTENTIONTOCELL, second=cell)
            minimap._Minimap__parentUI.chatCommands._ChatCommandsController__sendChatCommand(decorator)

        if params['timeEndMessage']:
            BigWorld.callback(params['timeEndMessage'], show_observed_end_message)

def custom_handleKey(self, isDown, key, mods):
    orig_handleKey(self, isDown, key, mods)

    if (key == Keys.KEY_F10 and isDown) or (key == Keys.KEY_F and isDown and BigWorld.isKeyDown(Keys.KEY_LCONTROL)):
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