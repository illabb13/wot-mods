# coding=utf-8

__author__ = "illabb13"
__copyright__ = "Copyright 2014, illabb13"
__version__ = '0.7 (WoT 0.9.1)'
__email__ = "illabb13@gmail.com"

import BigWorld
import ResMgr
import Keys
from Avatar import PlayerAvatar
from constants import VEHICLE_MISC_STATUS
from ChatManager import chatManager
from gui.WindowsManager import g_windowsManager
from constants import ARENA_GUI_TYPE

# ======================================================================================================================
# дефолтные настройки
params = {
    'isEnabled': 0,  # кандидат на удаление
    'disabledByStartBattle': 1,
    'showWhenLess': 6,
    'limitationTypeOfBattles': 1,
    'message': 'Меня засветили, япона мать! :)',
    'withoutHelpMe': 0,
    'time': 8,
    'endMessage': 'Прошло {time} секунд. Возможно ты уже не в засвете. Вперед за дамажкой!',
    'enableHotKey': 1,
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
    message = params['endMessage'].format(time=params['time'])
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
        self.broadcast(team_channel_id, params['message'])
        if not params['withoutHelpMe']:
            self.broadcast(team_channel_id, '/HELPME')
        BigWorld.callback(params['time'], show_observed_end_message)

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