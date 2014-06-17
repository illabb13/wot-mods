# coding=utf-8

__author__ = "illabb13"
__copyright__ = "Copyright 2014, illabb13"
__version__ = '0.6'
__email__ = "illabb13@gmail.com"

import BigWorld
import ResMgr
import Keys
from Avatar import PlayerAvatar
from constants import VEHICLE_MISC_STATUS
from ChatManager import chatManager
from gui.WindowsManager import g_windowsManager

# ======================================================================================================================
# дефолтные настройки
params = {
    'isEnabled': 1,
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
orig_updateVehicleMiscStatus = PlayerAvatar.updateVehicleMiscStatus
orig_handleKey = PlayerAvatar.handleKey

# кастомные функции
def custom_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg):
    orig_updateVehicleMiscStatus(self, vehicleID, code, intArg, floatArg)

    if params['isEnabled'] and code == VEHICLE_MISC_STATUS.IS_OBSERVED_BY_ENEMY:
        team_channel_id = chatManager.battleTeamChannelID
        self.broadcast(team_channel_id, params['message'])
        if not params['withoutHelpMe']:
            self.broadcast(team_channel_id, '/HELPME')
        BigWorld.callback(params['time'], show_observed_end_message)


def custom_handleKey(self, isDown, key, mods):
    orig_handleKey(self, isDown, key, mods)

    if BigWorld.isKeyDown(Keys.KEY_LCONTROL) and isDown and key == Keys.KEY_F:
        params['isEnabled'] = not params['isEnabled']
        message = 'Observed Mod ВКЛЮЧЕН' if params['isEnabled'] else 'Observed Mod ОТКЛЮЧЕН'
        show_player_panel_message(message)

# ======================================================================================================================
# основная часть
PlayerAvatar.updateVehicleMiscStatus = custom_updateVehicleMiscStatus
if params['enableHotKey']:
    PlayerAvatar.handleKey = custom_handleKey