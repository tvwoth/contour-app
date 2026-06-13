import json
import os
import re
from typing import Any, Optional

VIRTUAL_CUSTOM_CONFIG = 'Пользовательская конфигурация'
H_PARAM_KEYS = (
    'j_x', 'c_x', 'cd_len', 'de_len', 'fg_len',
    'gh_len', 'hi_len', 'jk_len', 'hcor',
)
MAX_CONFIG_NAME_LEN = 100
MAX_CONFIG_FILE_SIZE = 4096


class ConfigRepository:
    def __init__(self, app_dir: str, user_configs_dir: Optional[str] = None):
        self.app_dir = app_dir
        self.system_dir = os.path.join(app_dir, 'configs')
        self.user_dir = user_configs_dir or os.environ.get(
            'USER_CONFIGS_DIR',
            os.path.join(app_dir, 'user_configs'),
        )
        self.ensure_user_dir()

    def ensure_user_dir(self) -> None:
        try:
            os.makedirs(self.user_dir, exist_ok=True)
        except OSError:
            self.user_dir = None
            return

        if not os.path.isdir(self.user_dir):
            self.user_dir = None
            return

    def list_system_configs(self) -> list[str]:
        if not os.path.isdir(self.system_dir):
            return []
        names = [
            os.path.splitext(f)[0]
            for f in os.listdir(self.system_dir)
            if f.endswith('.json')
        ]
        return sorted(names, key=lambda name: (name != 'задайте значения', name))

    def list_user_configs(self) -> list[str]:
        if not self.user_dir or not os.path.isdir(self.user_dir):
            return []
        names = [
            os.path.splitext(f)[0]
            for f in os.listdir(self.user_dir)
            if f.endswith('.json')
        ]
        return sorted(names)

    def all_selectable_configs(self) -> list[str]:
        return self.list_system_configs() + self.list_user_configs() + [VIRTUAL_CUSTOM_CONFIG]

    def sanitize_config_name(self, name: str) -> str:
        name = (name or '').strip()
        if not name:
            raise ValueError('Имя конфигурации не может быть пустым')
        if len(name) > MAX_CONFIG_NAME_LEN:
            raise ValueError(f'Имя конфигурации не длиннее {MAX_CONFIG_NAME_LEN} символов')
        if '..' in name or '/' in name or '\\' in name:
            raise ValueError('Имя не должно содержать .., / или \\')
        if name == VIRTUAL_CUSTOM_CONFIG:
            raise ValueError('Зарезервированное имя конфигурации')
        if not re.match(r'^[\w\- ]+$', name, re.UNICODE):
            raise ValueError('Имя может содержать только буквы, цифры, пробелы, _ и -')
        if self.is_system_config(name):
            raise ValueError('Нельзя использовать имя системного пресета')
        return name

    def is_system_config(self, name: str) -> bool:
        return os.path.isfile(os.path.join(self.system_dir, f'{name}.json'))

    def is_user_config(self, name: str) -> bool:
        if not self.user_dir:
            return False
        return os.path.isfile(os.path.join(self.user_dir, f'{name}.json'))

    def resolve_config_path(self, name: str) -> Optional[str]:
        if name == VIRTUAL_CUSTOM_CONFIG:
            return None
        system_path = os.path.join(self.system_dir, f'{name}.json')
        if os.path.isfile(system_path):
            return system_path
        if not self.user_dir:
            return None
        user_path = os.path.join(self.user_dir, f'{name}.json')
        if os.path.isfile(user_path):
            return user_path
        return None

    def to_config_dict(self, calculator) -> dict[str, Any]:
        return {
            'j_x': calculator.J_X,
            'c_x': calculator.C_X,
            'cd_len': calculator.CD_LEN,
            'de_len': calculator.DE_LEN,
            'fg_len': calculator.FG_LEN,
            'gh_len': calculator.GH_LEN,
            'hi_len': calculator.HI_LEN,
            'jk_len': calculator.JK_LEN,
            'hcor': calculator.HCOR,
            'image': None,
        }

    def validate_h_params(self, data: dict[str, Any]) -> dict[str, float]:
        result: dict[str, float] = {}
        for key in H_PARAM_KEYS:
            if key not in data or data[key] is None:
                raise ValueError(f'Поле {key} обязательно и должно быть числом')
            try:
                value = float(data[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f'Поле {key} должно быть числом') from exc
            result[key] = value
        return result

    def save_user_config(self, name: str, data: dict[str, Any]) -> str:
        if not self.user_dir:
            raise ValueError('Каталог пользовательских конфигураций недоступен для записи')

        safe_name = self.sanitize_config_name(name)
        validated = self.validate_h_params(data)
        payload = {**validated, 'image': None}

        try:
            os.makedirs(self.user_dir, exist_ok=True)
        except OSError as e:
            raise ValueError(f'Не удалось создать директорию конфигураций: {str(e)}')

        path = os.path.join(self.user_dir, f'{safe_name}.json')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
        except IOError as e:
            raise ValueError(f'Не удалось сохранить файл конфигурации: {str(e)}')
        except json.JSONDecodeError as e:
            raise ValueError(f'Ошибка кодирования JSON: {str(e)}')

        return safe_name

    def load_user_config(self, name: str) -> dict[str, Any]:
        if not self.user_dir or not self.is_user_config(name):
            raise ValueError('Пользовательская конфигурация не найдена')
        path = os.path.join(self.user_dir, f'{name}.json')

        if os.path.getsize(path) > MAX_CONFIG_FILE_SIZE:
            raise ValueError('Файл конфигурации слишком большой')

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except IOError as e:
            raise ValueError(f'Не удалось прочитать файл конфигурации: {str(e)}')
        except json.JSONDecodeError as e:
            raise ValueError(f'Ошибка формата JSON в файле конфигурации: {str(e)}')

        return data

    def delete_user_config(self, name: str) -> None:
        if self.is_system_config(name):
            raise ValueError('Нельзя удалить системный пресет')
        if not self.is_user_config(name):
            raise ValueError('Пользовательская конфигурация не найдена')
        path = os.path.join(self.user_dir, f'{name}.json')
        os.remove(path)

    def rename_user_config(self, old_name: str, new_name: str) -> str:
        if self.is_system_config(old_name):
            raise ValueError('Нельзя переименовать системный пресет')
        if not self.is_user_config(old_name):
            raise ValueError('Пользовательская конфигурация не найдена')
        safe_new = self.sanitize_config_name(new_name)
        old_path = os.path.join(self.user_dir, f'{old_name}.json')
        new_path = os.path.join(self.user_dir, f'{safe_new}.json')
        if os.path.isfile(new_path) and safe_new != old_name:
            raise ValueError('Конфигурация с таким именем уже существует')
        os.rename(old_path, new_path)
        return safe_new

    def params_match_saved(self, params: dict[str, Optional[float]], config_data: dict) -> bool:
        for key in H_PARAM_KEYS:
            current = params.get(key)
            saved = config_data.get(key, 0)
            if current is None:
                continue
            if abs(current - saved) >= 1e-6:
                return False
        return True


def parse_h_params(form) -> dict[str, Optional[float]]:
    def parse_float(key: str) -> Optional[float]:
        raw = form.get(key)
        if raw is None or raw == '':
            return None
        return float(raw)

    j_x = -abs(parse_float('j_x')) if form.get('j_x') else None
    c_x = -abs(parse_float('c_x')) if form.get('c_x') else None
    return {
        'j_x': j_x,
        'c_x': c_x,
        'cd_len': parse_float('cd_len'),
        'de_len': parse_float('de_len'),
        'fg_len': parse_float('fg_len'),
        'gh_len': parse_float('gh_len'),
        'hi_len': parse_float('hi_len'),
        'jk_len': parse_float('jk_len'),
        'hcor': parse_float('hcor'),
    }


def apply_h_params(calculator, params: dict[str, Optional[float]]) -> None:
    calculator.set_j_x(params['j_x'])
    calculator.set_c_x(params['c_x'])
    calculator.set_cd_len(params['cd_len'])
    calculator.set_de_len(params['de_len'])
    calculator.set_fg_len(params['fg_len'])
    calculator.set_gh_len(params['gh_len'])
    calculator.set_hi_len(params['hi_len'])
    calculator.set_jk_len(params['jk_len'])
    calculator.set_hcor(params['hcor'])
