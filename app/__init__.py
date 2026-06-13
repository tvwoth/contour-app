import json
import os
import secrets
import time
from datetime import timedelta
from itertools import zip_longest

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .calculator.contour_calculator import ContourCalculator, generate_plot
from .config_service import (
    VIRTUAL_CUSTOM_CONFIG,
    ConfigRepository,
    apply_h_params,
    parse_h_params,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(
    hours=int(os.environ.get('CONFIG_ADMIN_SESSION_HOURS', '2'))
)

app.jinja_env.globals.update(zip=zip_longest)

config_images = {
    'Премьер комплект YP01YP02YP03G01': 'default_config.png',
    'Синдикат КЗ471КЗ472КЗ473': 'test_config.png',
    'задайте значения': '',
    VIRTUAL_CUSTOM_CONFIG: '',
}

APP_DIR = os.path.dirname(__file__)
config_repo = ConfigRepository(APP_DIR)
calculator = ContourCalculator()


def get_admin_password() -> str:
    return os.environ.get('CONFIG_ADMIN_PASSWORD', 'admin')


def is_config_admin() -> bool:
    if not session.get('config_admin'):
        return False
    expires = session.get('config_admin_expires')
    if expires is not None and time.time() > expires:
        session.pop('config_admin', None)
        session.pop('config_admin_expires', None)
        return False
    return True


def require_config_admin():
    if not is_config_admin():
        abort(403)


def login_config_admin(password: str) -> bool:
    if password == get_admin_password():
        session.permanent = True
        session['config_admin'] = True
        session['config_admin_expires'] = time.time() + app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        return True
    return False


def logout_config_admin():
    session.pop('config_admin', None)
    session.pop('config_admin_expires', None)


def get_config_name_field(selected_config: str) -> str:
    if config_repo.is_user_config(selected_config):
        return selected_config
    return ''


def load_config_by_name(name: str):
    if name == VIRTUAL_CUSTOM_CONFIG:
        return None
    path = config_repo.resolve_config_path(name)
    if not path:
        raise FileNotFoundError(f'Конфигурация «{name}» не найдена')
    return calculator.load_config(path)


def detect_custom_config(selected_config: str, params: dict) -> str:
    if selected_config == VIRTUAL_CUSTOM_CONFIG:
        return selected_config
    path = config_repo.resolve_config_path(selected_config)
    if not path:
        return VIRTUAL_CUSTOM_CONFIG
    with open(path, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    if not config_repo.params_match_saved(params, config_data):
        return VIRTUAL_CUSTOM_CONFIG
    return selected_config


def render_index(**kwargs):
    preset_configs = config_repo.list_system_configs()
    user_configs = config_repo.list_user_configs()
    defaults = {
        'calculator': calculator,
        'preset_configs': preset_configs,
        'user_configs': user_configs,
        'config_admin': is_config_admin(),
        'config_name_field': get_config_name_field(kwargs.get('selected_config', 'задайте значения')),
        'config_images': config_images,
    }
    defaults.update(kwargs)
    return render_template('index.html', **defaults)


@app.route('/', methods=['GET', 'POST'])
def index():
    selected_config = 'задайте значения'
    results = None
    plot_url = None
    abs_j_x = None
    abs_c_x = None
    image_path = None
    config_name_field = ''

    if request.method == 'POST':
        action = request.form.get('action')
        form_config = request.form.get('config', selected_config)
        all_configs = config_repo.all_selectable_configs()

        if action == 'load_config':
            selected_config = form_config if form_config in all_configs else 'задайте значения'
            if selected_config != VIRTUAL_CUSTOM_CONFIG:
                try:
                    image_path = load_config_by_name(selected_config)
                    flash('Конфигурация успешно загружена.', 'success')
                except Exception as e:
                    flash(f'Ошибка загрузки конфигурации: {str(e)}', 'error')
            config_name_field = get_config_name_field(selected_config)

        elif action == 'reset_config':
            calculator.__init__()
            selected_config = 'задайте значения'
            flash('Параметры сброшены.', 'success')

        elif action == 'calculate':
            try:
                n1 = float(request.form.get('n1')) if request.form.get('n1') else None
                n2 = float(request.form.get('n2')) if request.form.get('n2') else None
                n3 = float(request.form.get('n3')) if request.form.get('n3') else None
                angle_EF = float(request.form.get('angle_EF')) if request.form.get('angle_EF') else None
                rev = request.form.get('rev') == 'on'

                params = parse_h_params(request.form)
                apply_h_params(calculator, params)
                calculator.set_directions(REV=rev)

                points = calculator.calculate(n1, n2, n3, angle_EF)
                plot_path = os.path.join(APP_DIR, 'static', 'plot.png')
                generate_plot(points, output_path=plot_path)
                plot_url = url_for('static', filename='plot.png')

                results = {
                    'n1': calculator.n1,
                    'n2': calculator.n2,
                    'n3': calculator.get_n3(),
                    'angle': calculator.get_angle_EF(),
                    'rev': calculator.REV,
                    'h1': abs(calculator.J_X) if calculator.J_X is not None else None,
                    'h2': abs(calculator.C_X) if calculator.C_X is not None else None,
                    'h3': calculator.CD_LEN,
                    'h4': calculator.DE_LEN,
                    'h5': calculator.FG_LEN,
                    'h6': calculator.GH_LEN,
                    'h7': calculator.HI_LEN,
                    'h8': calculator.JK_LEN,
                    'hcor': calculator.HCOR,
                    'points': points,
                }

                base_config = form_config if form_config in all_configs else VIRTUAL_CUSTOM_CONFIG
                selected_config = detect_custom_config(base_config, params)
                config_name_field = get_config_name_field(selected_config)
                flash('Расчёт выполнен успешно.', 'success')
            except ValueError as e:
                flash(f'Ошибка ввода: {str(e)}', 'error')
            except Exception as e:
                flash(f'Ошибка расчёта: {str(e)}', 'error')

    if request.method == 'GET':
        config_query = request.args.get('config')
        all_configs = config_repo.all_selectable_configs()
        if config_query and config_query in all_configs:
            selected_config = config_query
            if config_query != VIRTUAL_CUSTOM_CONFIG:
                try:
                    image_path = load_config_by_name(config_query)
                except Exception:
                    pass
            config_name_field = get_config_name_field(selected_config)

    abs_j_x = abs(calculator.J_X) if calculator.J_X is not None else None
    abs_c_x = abs(calculator.C_X) if calculator.C_X is not None else None

    if not config_name_field:
        config_name_field = get_config_name_field(selected_config)

    return render_index(
        selected_config=selected_config,
        results=results,
        plot_url=plot_url,
        abs_j_x=abs_j_x,
        abs_c_x=abs_c_x,
        image_path=image_path,
        config_name_field=config_name_field,
    )


@app.route('/config_admin/login', methods=['POST'])
def config_admin_login():
    password = request.form.get('admin_password', '')
    if login_config_admin(password):
        flash('Режим редактирования конфигураций включён.', 'success')
    else:
        flash('Неверный пароль администратора.', 'error')
    return redirect(url_for('index'))


@app.route('/config_admin/logout', methods=['POST'])
def config_admin_logout():
    logout_config_admin()
    flash('Режим редактирования конфигураций выключен.', 'success')
    return redirect(url_for('index'))


@app.route('/save_config', methods=['POST'])
def save_config():
    require_config_admin()
    config_name = request.form.get('config_name', '').strip()
    try:
        if not config_name:
            raise ValueError('Пожалуйста, введите имя конфигурации')
        params = parse_h_params(request.form)
        apply_h_params(calculator, params)
        saved_name = config_repo.save_user_config(config_name, params)
        flash(f'Конфигурация «{saved_name}» сохранена.', 'success')
        return redirect(url_for('index', config=saved_name))
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Ошибка сохранения: {str(e)}', 'error')
    return redirect(url_for('index'))


@app.route('/delete_config', methods=['POST'])
def delete_config():
    require_config_admin()
    config_name = request.form.get('config_name', '').strip()
    try:
        if not config_name:
            config_name = request.form.get('config', '').strip()
        config_repo.delete_user_config(config_name)
        flash(f'Конфигурация «{config_name}» удалена.', 'success')
        return redirect(url_for('index'))
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Ошибка удаления: {str(e)}', 'error')
    return redirect(url_for('index'))


@app.route('/rename_config', methods=['POST'])
def rename_config():
    require_config_admin()
    old_name = request.form.get('config', '').strip()
    new_name = request.form.get('config_name', '').strip()
    try:
        renamed = config_repo.rename_user_config(old_name, new_name)
        flash(f'Конфигурация переименована в «{renamed}».', 'success')
        return redirect(url_for('index', config=renamed))
    except ValueError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Ошибка переименования: {str(e)}', 'error')
    return redirect(url_for('index'))


@app.route('/save_config', methods=['GET'])
@app.route('/delete_config', methods=['GET'])
@app.route('/rename_config', methods=['GET'])
def config_admin_routes_get():
    abort(405)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
