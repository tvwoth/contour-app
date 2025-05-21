import math
import json
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

class ContourCalculator:
    def __init__(self):
        self.A_X = 0
        self.A_Y = 0
        self.B_X = self.A_X
        self.C_X = 0
        self.D_X = self.C_X
        self.CD_LEN = 0
        self.DE_LEN = 0
        self.FG_LEN = 0
        self.GH_LEN = 0
        self.HI_LEN = 0
        self.J_X = 0
        self.JK_LEN = 0
        self.HCOR = 0
        self.K_X = self.J_X
        self.K_Y = self.A_Y
        self.REV = False
        self.n1 = None
        self.n2 = None
        self.n4 = None
        self.angle_D = None
        self.alpha = None
        self.angle_EF = None
        self.load_config(os.path.join(os.path.dirname(__file__), "configs", "default.json"))

    def load_config(self, config_file=None):
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                self.set_j_x(config.get("j_x", self.J_X))
                self.set_c_x(config.get("c_x", self.C_X))
                self.set_cd_len(config.get("cd_len", self.CD_LEN))
                self.set_de_len(config.get("de_len", self.DE_LEN))
                self.set_fg_len(config.get("fg_len", self.FG_LEN))
                self.set_gh_len(config.get("gh_len", self.GH_LEN))
                self.set_hi_len(config.get("hi_len", self.HI_LEN))
                self.set_jk_len(config.get("jk_len", self.JK_LEN))
                self.set_hcor(config.get("hcor", self.HCOR))
                return config.get("image")
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Ошибка чтения {config_file}: {e}, используются значения по умолчанию")
        return None

    def set_j_x(self, j_x):
        self.J_X = j_x
        self.K_X = j_x

    def set_c_x(self, c_x):
        self.C_X = c_x
        self.D_X = c_x

    def set_cd_len(self, cd_len):
        self.CD_LEN = cd_len

    def set_de_len(self, de_len):
        self.DE_LEN = de_len

    def set_fg_len(self, fg_len):
        self.FG_LEN = fg_len

    def set_gh_len(self, gh_len):
        self.GH_LEN = gh_len

    def set_hi_len(self, hi_len):
        self.HI_LEN = hi_len

    def set_jk_len(self, jk_len):
        self.JK_LEN = jk_len

    def set_hcor(self, hcor):
        self.HCOR = hcor

    def set_directions(self, REV=None):
        if REV is not None:
            self.REV = REV

    def calculate(self, n1, n2, n4, angle_EF):
        params = {'n1': n1, 'n2': n2, 'n4': n4, 'angle_EF': angle_EF}
        given_params = sum(1 for v in params.values() if v is not None)
        if given_params != 3:
            raise ValueError("Необходимо ввести ровно три параметра")

        if angle_EF is not None:
            if not (0 <= angle_EF <= 10):
                raise ValueError("Угол наклона должен быть в диапазоне 0°–10°")
            self.angle_D = 180 + angle_EF
        else:
            self.angle_D = None

        for name, value in params.items():
            if value is not None and value <= 0 and name != 'angle_EF':
                raise ValueError(f"Длина {name} должна быть положительной")

        if all(v == 0 for v in [self.C_X, self.CD_LEN, self.DE_LEN, self.FG_LEN, self.GH_LEN, self.HI_LEN, self.J_X, self.JK_LEN]):
            raise ValueError("Выберите конфигурацию или введите значения H")

        self.n1 = n1
        self.n2 = n2
        self.n4 = n4 if n4 is None else n4 + self.HCOR
        self.angle_EF = angle_EF

        if self.n1 is None:
            self.n1 = self._calculate_missing_n1(self.n2, self.n4, angle_EF)
        elif self.n2 is None:
            self.n2 = self._calculate_missing_n2(self.n1, self.n4, angle_EF)
        elif self.n4 is None:
            self.n4 = self._calculate_missing_n4(self.n1, self.n2, angle_EF)
        elif self.angle_EF is None:
            self.angle_D = self._calculate_missing_angle_D(self.n1, self.n2, self.n4)
            self.angle_EF = self.angle_D - 180

        self.alpha = 270 - self.angle_D
        points = self.calculate_points()
        return points

    def _calculate_points_to_i(self, n1, n2, angle_D):
        alpha_rad = math.radians(270 - angle_D)
        cos_alpha = math.cos(alpha_rad)
        sin_alpha = math.sin(alpha_rad)
        points = [
            (self.A_X, self.A_Y),  # A
            (self.B_X, -n1),       # B
            (self.C_X, -n1),       # C
        ]
        c_x, c_y = points[2]
        d_y = c_y + self.CD_LEN if self.REV else c_y - self.CD_LEN
        points.append((self.D_X, d_y))  # D
        d_x, d_y = points[3]
        e_x = d_x - self.DE_LEN * cos_alpha if self.REV else d_x + self.DE_LEN * cos_alpha
        e_y = d_y + self.DE_LEN * sin_alpha if self.REV else d_y - self.DE_LEN * sin_alpha
        points.append((e_x, e_y))  # E
        e_x, e_y = points[4]
        f_x = e_x + n2 * math.cos(alpha_rad + math.pi / 2)
        f_y = e_y - n2 * math.sin(alpha_rad + math.pi / 2)
        points.append((f_x, f_y))  # F
        points.append((f_x - self.FG_LEN * cos_alpha, f_y + self.FG_LEN * sin_alpha))  # G
        g_x, g_y = points[6]
        points.append((g_x, g_y + self.GH_LEN))  # H
        points.append((g_x + self.HI_LEN, g_y + self.GH_LEN))  # I
        return points

    def _calculate_missing_n1(self, n2, n4, angle_EF):
        angle_D = 180 + angle_EF
        def calc_n4(n1):
            points = self._calculate_points_to_i(n1, n2, angle_D)
            i_x, i_y = points[8]
            j_x, j_y = self.J_X, self.K_Y - self.JK_LEN
            return math.sqrt((i_x - j_x) ** 2 + (i_y - j_y) ** 2)

        n1_min, n1_max = 0, 3000
        tolerance = 0.01
        for _ in range(100):
            n1_mid = (n1_min + n1_max) / 2
            error = calc_n4(n1_mid) - n4
            if abs(error) < tolerance:
                return n1_mid
            elif error > 0:
                n1_max = n1_mid
            else:
                n1_min = n1_mid
        raise ValueError("Не удалось найти длину n1")

    def _calculate_missing_n2(self, n1, n4, angle_EF):
        angle_D = 180 + angle_EF
        def calc_n4(n2):
            points = self._calculate_points_to_i(n1, n2, angle_D)
            i_x, i_y = points[8]
            j_x, j_y = self.J_X, self.K_Y - self.JK_LEN
            return math.sqrt((i_x - j_x) ** 2 + (i_y - j_y) ** 2)

        n2_min, n2_max = 0, 3000
        tolerance = 0.01
        for _ in range(100):
            n2_mid = (n2_min + n2_max) / 2
            error = calc_n4(n2_mid) - n4
            if abs(error) < tolerance:
                return n2_mid
            elif error > 0:
                n2_max = n2_mid
            else:
                n2_min = n2_mid
        raise ValueError("Не удалось найти длину n2")

    def _calculate_missing_n4(self, n1, n2, angle_EF):
        angle_D = 180 + angle_EF
        points = self._calculate_points_to_i(n1, n2, angle_D)
        i_x, i_y = points[8]
        j_x, j_y = self.J_X, self.K_Y - self.JK_LEN
        n4 = math.sqrt((i_x - j_x) ** 2 + (i_y - j_y) ** 2)
        return n4

    def _calculate_missing_angle_D(self, n1, n2, n4):
        def calc_n4(angle_D_rad):
            alpha_rad = math.radians(270 - math.degrees(angle_D_rad))
            cos_alpha = math.cos(alpha_rad)
            sin_alpha = math.sin(alpha_rad)
            points = [
                (self.A_X, self.A_Y),  # A
                (self.B_X, -n1),       # B
                (self.C_X, -n1),       # C
            ]
            c_x, c_y = points[2]
            d_y = c_y + self.CD_LEN if self.REV else c_y - self.CD_LEN
            points.append((self.D_X, d_y))  # D
            d_x, d_y = points[3]
            e_x = d_x - self.DE_LEN * cos_alpha if self.REV else d_x + self.DE_LEN * cos_alpha
            e_y = d_y + self.DE_LEN * sin_alpha if self.REV else d_y - self.DE_LEN * sin_alpha
            points.append((e_x, e_y))  # E
            e_x, e_y = points[4]
            f_x = e_x + n2 * math.cos(alpha_rad + math.pi / 2)
            f_y = e_y - n2 * math.sin(alpha_rad + math.pi / 2)
            points.append((f_x, f_y))  # F
            points.append((f_x - self.FG_LEN * cos_alpha, f_y + self.FG_LEN * sin_alpha))  # G
            g_x, g_y = points[6]
            points.append((g_x, g_y + self.GH_LEN))  # H
            points.append((g_x + self.HI_LEN, g_y + self.GH_LEN))  # I
            i_x, i_y = points[8]
            j_x, j_y = self.J_X, self.K_Y - self.JK_LEN
            return math.sqrt((i_x - j_x) ** 2 + (i_y - j_y) ** 2)

        D_min = math.radians(0)
        D_max = math.radians(360)
        tolerance = 0.01
        max_iterations = 100
        current_D = math.radians(180)
        step = math.radians(10)
        calculated_n4 = calc_n4(current_D)

        for _ in range(max_iterations):
            error = calculated_n4 - n4
            if abs(error) < tolerance:
                return math.degrees(current_D)
            if error > 0:
                D_max = current_D
                current_D = (D_min + current_D) / 2
            else:
                D_min = current_D
                current_D = (current_D + D_max) / 2
            calculated_n4 = calc_n4(current_D)

        raise ValueError("Не удалось найти угол D. Возможно, заданная длина IJ недостижима.")

    def calculate_a(self):
        return (self.A_X, self.A_Y)

    def calculate_b(self):
        return (self.B_X, -self.n1)

    def calculate_c(self):
        return (self.C_X, -self.n1)

    def calculate_d(self, c_y):
        d_y = c_y + self.CD_LEN if self.REV else c_y - self.CD_LEN
        return (self.D_X, d_y)

    def calculate_e(self, d_x, d_y, alpha_rad):
        cos_alpha = math.cos(alpha_rad)
        sin_alpha = math.sin(alpha_rad)
        e_x = d_x - self.DE_LEN * cos_alpha if self.REV else d_x + self.DE_LEN * cos_alpha
        e_y = d_y + self.DE_LEN * sin_alpha if self.REV else d_y - self.DE_LEN * sin_alpha
        return (e_x, e_y)

    def calculate_f(self, e_x, e_y, alpha_rad):
        f_x = e_x + self.n2 * math.cos(alpha_rad + math.pi / 2)
        f_y = e_y - self.n2 * math.sin(alpha_rad + math.pi / 2)
        return (f_x, f_y)

    def calculate_g(self, f_x, f_y, alpha_rad):
        cos_alpha = math.cos(alpha_rad)
        sin_alpha = math.sin(alpha_rad)
        return (f_x - self.FG_LEN * cos_alpha, f_y + self.FG_LEN * sin_alpha)

    def calculate_h(self, g_x, g_y):
        return (g_x, g_y + self.GH_LEN)

    def calculate_i(self, g_x, g_y):
        return (g_x + self.HI_LEN, g_y + self.GH_LEN)

    def calculate_j(self):
        return (self.J_X, self.K_Y - self.JK_LEN)

    def calculate_k(self):
        return (self.K_X, self.K_Y)

    def calculate_points(self):
        if any(x is None for x in [self.n1, self.n2, self.n4, self.angle_D]):
            raise ValueError("Одно или несколько параметров не определены")
        alpha_rad = math.radians(self.alpha)
        points = [
            self.calculate_a(),
            self.calculate_b(),
            self.calculate_c(),
        ]
        c_x, c_y = points[2]
        points.append(self.calculate_d(c_y))
        d_x, d_y = points[3]
        points.append(self.calculate_e(d_x, d_y, alpha_rad))
        e_x, e_y = points[4]
        points.append(self.calculate_f(e_x, e_y, alpha_rad))
        f_x, f_y = points[5]
        points.append(self.calculate_g(f_x, f_y, alpha_rad))
        g_x, g_y = points[6]
        points.append(self.calculate_h(g_x, g_y))
        points.append(self.calculate_i(g_x, g_y))
        points.append(self.calculate_j())
        points.append(self.calculate_k())
        return points

    def get_n3(self):
        return self.n4 - self.HCOR if self.n4 is not None else None

    def get_angle_EF(self):
        return self.angle_D - 180

def generate_plot(points, output_path="static/plot.png"):
    fig, ax = plt.subplots(figsize=(6, 4))
    x = [p[0] for p in points] + [points[0][0]]
    y = [p[1] for p in points] + [points[0][1]]
    ax.plot(x, y, marker='o')
    labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    for i, (label, (px, py)) in enumerate(zip(labels, points)):
        ax.annotate(label, (px, py), xytext=(5, 5), textcoords='offset points')
    coords_text = "\n".join([f"{label}: ({p[0]:.2f}, {p[1]:.2f})" for label, p in zip(labels, points)])
    ax.text(0.05, 0.95, coords_text, transform=ax.transAxes, fontsize=8, verticalalignment='top')
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True)
    ax.invert_yaxis()
    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)
    x_margin = (x_max - x_min) * 0.1 or 50
    y_margin = (y_max - y_min) * 0.1 or 50
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    plt.savefig(output_path, bbox_inches='tight')
    plt.close(fig)