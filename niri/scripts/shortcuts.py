#!/usr/bin/python3
"""Searchable reference for this Niri configuration. Selecting a row executes nothing."""
from pathlib import Path
import re
import shlex
import subprocess
import sys

DESCRIPTIONS = {
 'close-window':'Окна · Закрыть окно',
 'focus-column-left':'Окна · Фокус колонки слева',
 'focus-column-right':'Окна · Фокус колонки справа',
 'focus-window-down':'Окна · Фокус окна ниже в колонке',
 'focus-window-up':'Окна · Фокус окна выше в колонке',
 'move-column-left':'Окна · Переместить колонку влево',
 'move-column-right':'Окна · Переместить колонку вправо',
 'move-window-down':'Окна · Переместить окно вниз',
 'move-window-up':'Окна · Переместить окно вверх',
 'fullscreen-window':'Окна · Полноэкранный режим',
 'toggle-window-floating':'Окна · Плавающее / тайлинговое окно',
 'switch-focus-between-floating-and-tiling':'Окна · Фокус плавающих / тайлинговых окон',
 'center-column':'Размер · Центрировать колонку',
 'switch-preset-column-width':'Размер · Ширина колонки: ⅓ → ½ → ⅔',
 'set-column-width':'Размер · Ширина колонки',
 'set-window-height':'Размер · Высота окна',
 'maximize-column':'Размер · Колонка на всю ширину экрана',
 'consume-or-expel-window-left':'Колонки · Включить / извлечь окно слева',
 'consume-or-expel-window-right':'Колонки · Включить / извлечь окно справа',
 'focus-workspace-up':'Пространства · Предыдущее пространство',
 'focus-workspace-down':'Пространства · Следующее пространство',
 'move-window-to-workspace-up':'Пространства · Перенести окно в предыдущее',
 'move-window-to-workspace-down':'Пространства · Перенести окно в следующее',
 'focus-workspace':'Пространства · Перейти в',
 'move-window-to-workspace':'Пространства · Перенести окно в',
 'focus-monitor-left':'Мониторы · Фокус монитора слева',
 'focus-monitor-right':'Мониторы · Фокус монитора справа',
 'move-column-to-monitor-left':'Мониторы · Перенести колонку на левый монитор',
 'move-column-to-monitor-right':'Мониторы · Перенести колонку на правый монитор',
 'toggle-overview':'Обзор · Все окна и пространства',
 'show-hotkey-overlay':'Помощь · Встроенная краткая подсказка',
 'toggle-keyboard-shortcuts-inhibit':'Система · Перехват сочетаний приложением: вкл./выкл.',
 'switch-layout':'Клавиатура · Переключить EN / RU',
 'screenshot':'Скриншоты · Выбрать область',
 'screenshot-screen':'Скриншоты · Активный экран',
 'screenshot-window':'Скриншоты · Активное окно',
 'quit':'Система · Выход из Niri с подтверждением',
}
SPAWN = {
 'Super+Return':'Запуск · Терминал Ghostty',
 'Super+D':'Запуск · Приложения Fuzzel',
 'Super+Shift+L':'Система · Заблокировать экран',
 'Super+V':'Буфер · История буфера обмена',
 'Super+Shift+V':'Буфер · Очистить историю и буфер',
 'Super+F1':'Помощь · Полный список сочетаний с поиском',
 'XF86AudioRaiseVolume':'Звук · Увеличить громкость на 5%',
 'XF86AudioLowerVolume':'Звук · Уменьшить громкость на 5%',
 'XF86AudioMute':'Звук · Выключить / включить звук',
 'XF86AudioMicMute':'Звук · Выключить / включить микрофон',
 'XF86AudioPlay':'Медиа · Воспроизведение / пауза',
 'XF86AudioNext':'Медиа · Следующий трек',
 'XF86AudioPrev':'Медиа · Предыдущий трек',
}
KEY_NAMES = {'Return':'Enter','Page_Up':'PageUp','Page_Down':'PageDown',
 'Minus':'−','Equal':'=','BracketLeft':'[','BracketRight':']','Slash':'/',
 'WheelScrollUp':'Колесо↑','WheelScrollDown':'Колесо↓',
 'XF86AudioRaiseVolume':'Volume+','XF86AudioLowerVolume':'Volume−',
 'XF86AudioMute':'Mute','XF86AudioMicMute':'Mic Mute',
 'XF86AudioPlay':'Play/Pause','XF86AudioNext':'Next','XF86AudioPrev':'Previous'}

def rows():
    config=Path.home()/'.config/niri/config.d/binds.kdl'
    result=[]
    # This setup uses one-line bind declarations; read descriptions and arguments live.
    for line in config.read_text().splitlines():
        match=re.match(r'^\s*(\S+)([^{}\n]*)\{\s*(.*?)\s*;\s*\}\s*$',line)
        if not match:
            continue
        key,properties,body=match.groups()
        args=shlex.split(body)
        if not args:
            continue
        action=args[0]
        title=re.search(r'hotkey-overlay-title="([^"]*)"',properties)
        if action in ('spawn','spawn-sh'):
            desc=SPAWN.get(key, title.group(1) if title else 'Запуск · '+' '.join(args[1:]))
        else:
            desc=DESCRIPTIONS.get(action,action)
            if action in ('focus-workspace','move-window-to-workspace','set-column-width','set-window-height'):
                desc+=' '+ ' '.join(args[1:])
        key=' + '.join(KEY_NAMES.get(part,part) for part in key.split('+'))
        result.append(f'{key:<31}  {desc}')
    result += [
      f'{"Super + ЛКМ, перетаскивание":<31}  Мышь · Переместить окно',
      f'{"Super + ПКМ, перетаскивание":<31}  Мышь · Изменить размер окна',
      f'{"Ctrl + Shift + C / V":<31}  Ghostty · Копировать / вставить',
      f'{"Меню Fedora → Выход и питание":<31}  Система · Блокировка, выход, перезагрузка, выключение',
    ]
    return result

if __name__=='__main__':
    text='\n'.join(rows())+'\n'
    if '--list' in sys.argv:
        print(text,end='')
    else:
        result=subprocess.run(['fuzzel','--dmenu','--prompt=Шорткаты ❯ ',
            '--width=94','--lines=18','--no-icons'],input=text,text=True,stdout=subprocess.DEVNULL)
        sys.exit(0 if result.returncode in (0,1,2) else result.returncode)
