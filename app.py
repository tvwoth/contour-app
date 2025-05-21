from flask import Flask, render_template, request, flash, url_for
from calculator.contour_calculator import ContourCalculator, generate_plot
import os
import json
import secrets
from itertools import zip_longest

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)

# Add zip to Jinja2 environment
app.jinja_env.globals.update(zip=zip_longest)

# Dictionary with paths to configuration help images
config_images = {
    'default': 'default_config.png',
    'test': 'test_config.png',
    'Пользовательская конфигурация': ''
}

calculator = ContourCalculator()

def get_config_options():
    config_dir = os.path.join(os.path.dirname(__file__), 'configs')
    configs = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    configs = [os.path.splitext(f)[0] for f in configs]
    configs.append('Пользовательская конфигурация')
    return configs

@app.route('/', methods=['GET', 'POST'])
def index():
    config_options = get_config_options()
    selected_config = 'default'  # Инициализация для GET-запросов
    results = None
    plot_url = None
    abs_j_x = None
    abs_c_x = None
    image_path = None

    if request.method == 'POST':
        action = request.form.get('action')
        # Получаем config из формы, сохраняем текущую конфигурацию
        form_config = request.form.get('config', selected_config)

        if action == 'load_config':
            selected_config = form_config if form_config in config_options else 'default'
            if selected_config != 'Пользовательская конфигурация':
                config_path = os.path.join(os.path.dirname(__file__), 'configs', f'{selected_config}.json')
                try:
                    image_path = calculator.load_config(config_path)
                    abs_j_x = abs(calculator.J_X) if calculator.J_X is not None else None
                    abs_c_x = abs(calculator.C_X) if calculator.C_X is not None else None
                    flash('Конфигурация успешно загружена.', 'success')
                except Exception as e:
                    flash(f'Ошибка загрузки конфигурации: {str(e)}', 'error')

        elif action == 'reset_config':
            calculator.__init__()
            abs_j_x = abs(calculator.J_X) if calculator.J_X is not None else None
            abs_c_x = abs(calculator.C_X) if calculator.C_X is not None else None
            selected_config = 'default'  # Сбрасываем на default
            flash('Параметры сброшены.', 'success')

        elif action == 'calculate':
            try:
                n1 = float(request.form.get('n1')) if request.form.get('n1') else None
                n2 = float(request.form.get('n2')) if request.form.get('n2') else None
                n3 = float(request.form.get('n3')) if request.form.get('n3') else None
                angle_EF = float(request.form.get('angle_EF')) if request.form.get('angle_EF') else None
                rev = request.form.get('rev') == 'on'

                # Преобразование j_x и c_x в отрицательные значения
                j_x = -abs(float(request.form.get('j_x'))) if request.form.get('j_x') else None
                c_x = -abs(float(request.form.get('c_x'))) if request.form.get('c_x') else None
                cd_len = float(request.form.get('cd_len')) if request.form.get('cd_len') else None
                de_len = float(request.form.get('de_len')) if request.form.get('de_len') else None
                fg_len = float(request.form.get('fg_len')) if request.form.get('fg_len') else None
                gh_len = float(request.form.get('gh_len')) if request.form.get('gh_len') else None
                hi_len = float(request.form.get('hi_len')) if request.form.get('hi_len') else None
                jk_len = float(request.form.get('jk_len')) if request.form.get('jk_len') else None
                hcor = float(request.form.get('hcor')) if request.form.get('hcor') else None

                calculator.set_j_x(j_x)
                calculator.set_c_x(c_x)
                calculator.set_cd_len(cd_len)
                calculator.set_de_len(de_len)
                calculator.set_fg_len(fg_len)
                calculator.set_gh_len(gh_len)
                calculator.set_hi_len(hi_len)
                calculator.set_jk_len(jk_len)
                calculator.set_hcor(hcor)
                calculator.set_directions(REV=rev)

                points = calculator.calculate(n1, n2, n3, angle_EF)
                generate_plot(points)
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
                    'points': points
                }
                # Сохраняем текущую конфигурацию или переключаем на Пользовательскую
                selected_config = form_config if form_config in config_options else 'Пользовательская конфигурация'
                # Проверяем, изменены ли параметры H
                config_path = os.path.join('configs', f'{form_config}.json')
                if os.path.exists(config_path) and form_config != 'Пользовательская конфигурация':
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        params_match = (
                            (j_x is None or abs(j_x - config_data.get('j_x', 0)) < 1e-6) and
                            (c_x is None or abs(c_x - config_data.get('c_x', 0)) < 1e-6) and
                            (cd_len is None or abs(cd_len - config_data.get('cd_len', 0)) < 1e-6) and
                            (de_len is None or abs(de_len - config_data.get('de_len', 0)) < 1e-6) and
                            (fg_len is None or abs(fg_len - config_data.get('fg_len', 0)) < 1e-6) and
                            (gh_len is None or abs(gh_len - config_data.get('gh_len', 0)) < 1e-6) and
                            (hi_len is None or abs(hi_len - config_data.get('hi_len', 0)) < 1e-6) and
                            (jk_len is None or abs(jk_len - config_data.get('jk_len', 0)) < 1e-6) and
                            (hcor is None or abs(hcor - config_data.get('hcor', 0)) < 1e-6)
                        )
                        if not params_match:
                            selected_config = 'Пользовательская конфигурация'
                flash('Расчёт выполнен успешно.', 'success')
            except ValueError as e:
                flash(f'Ошибка ввода: {str(e)}', 'error')
            except Exception as e:
                flash(f'Ошибка расчёта: {str(e)}', 'error')

    abs_j_x = abs(calculator.J_X) if calculator.J_X is not None else None
    abs_c_x = abs(calculator.C_X) if calculator.C_X is not None else None

    return render_template(
        'index.html',
        calculator=calculator,
        config_options=config_options,
        selected_config=selected_config,
        results=results,
        plot_url=plot_url,
        abs_j_x=abs_j_x,
        abs_c_x=abs_c_x,
        image_path=image_path,
        config_images=config_images
    )

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)