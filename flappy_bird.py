import random
import pygame
import pygame.freetype
import json


class Config:
    def __init__(self, config_path='bird_config.json'):
        self.config_path = config_path
        self.data = self.load_config()

    def load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print('Конфигурационный файл не найден')
            return {}

    def get(self, key):
        return self.data.get(key, {})


class GameObject:  # Базовый класс для всех игровых объектов
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.image = None
        self.rect = None

    def update(self):
        pass

    def draw(self, surface):
        if self.image and self.rect:
            surface.blit(self.image, self.rect)


class MovingObject(GameObject):  # Класс для движущихся объектов
    def __init__(self, x, y):
        super().__init__(x, y)
        self.speed = 0  # Добавляет свойства: скорость, направление
        self.dx = 0
        self.dy = 0

    def move(self):  # метод move() для перемещения
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        if self.rect:
            self.rect.x = self.x
            self.rect.y = self.y


class Bird(MovingObject):  # Класс птицы
    def __init__(self, x, y, config):
        super().__init__(x, y)
        bird_config = config.get('bird_settings')
        self.gravity = bird_config.get('gravity', 0.4)
        self.jump_strength = bird_config.get("jump_strength", -6)
        image_path = bird_config.get("image_path", "bird.png")
        self.width = bird_config.get("width", 60)
        self.height = bird_config.get("height", 35)
        self.speed_y = 0

        # Загрузка и масштабирование изображения
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (self.width, self.height))
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        # Применяем гравитацию
        self.speed_y += self.gravity
        self.y += self.speed_y
        self.rect.y = self.y

    def jump(self):  # делает прыжок
        self.speed_y = self.jump_strength

    def check_bounds(self, screen_height):
        # Проверка границ экрана
        if self.rect.top <= 0:
            self.rect.top = 0
            self.y = 0
            self.speed_y = 0
            return 'top'
        elif self.rect.bottom >= screen_height:
            self.rect.bottom = screen_height
            self.y = screen_height - self.rect.height
            return 'bottom'
        return None


class Wall(GameObject):  # Класс отдельной стены
    def __init__(self, x, y, config, flip=False):
        super().__init__(x, y)
        # Загрузка и подготовка изображения
        wall_config = config.get("wall_settings")
        self.speed = wall_config.get("speed", 2)
        width = wall_config.get("width", 100)
        height = wall_config.get("height", 500)

        image_path = wall_config.get("image_path", "wall.png")
        self.image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (width, height))
        if flip:
            self.image = pygame.transform.flip(self.image, False, True)

        self.rect = self.image.get_rect()
        if flip:
            self.rect.bottomleft = (x, y)  # Верхняя стена
        else:
            self.rect.topleft = (x, y)  # Нижняя стена

        self.passed = False
        self.flip = flip

    def update(self):
        # Движение стены влево
        self.x -= self.speed
        self.rect.x = self.x

    def is_offscreen(self):  # проверка ухода за экран
        # Проверка, ушла ли стена за экран
        return self.rect.right < 0

    def check_collision(self, bird_rect):
        # Проверка столкновения с птицей
        return self.rect.colliderect(bird_rect)

    def check_pass(self, bird_rect):
        # Проверка, прошла ли птица стену
        if not self.passed and self.rect.right < bird_rect.left:
            self.passed = True
            return True
        return False


class WallPair:  # Класс пары стен (верхняя + нижняя)
    def __init__(self, x, screen_height, config):  # Управляет двумя стенами как единым объектом
        wall_config = config.get('wall_settings')
        self.gap_height = wall_config.get("gap_height", 200)
        self.min_height = wall_config.get("min_height", 100)
        self.max_height = wall_config.get("max_height", 400)

        # Случайная высота для стен
        self.wall_height = random.randint(self.min_height, self.max_height)
        self.screen_height = screen_height

        # Создание верхней стены
        self.top_wall = Wall(x, self.wall_height, config, flip=True)

        # Создание нижней стены
        self.bottom_wall = Wall(x, self.wall_height + self.gap_height, config, flip=False)

        self.walls = [self.top_wall, self.bottom_wall]
        self.scored = False

    def update(self):
        for wall in self.walls:
            wall.update()

    def draw(self, surface):
        for wall in self.walls:
            wall.draw(surface)

    def check_collisions(self, bird_rect):
        for wall in self.walls:
            if wall.check_collision(bird_rect):
                return True
        return False

    def check_pass(self, bird_rect):
        if not self.scored:
            for wall in self.walls:
                if not wall.passed and wall.check_pass(bird_rect):
                    self.scored = True
                    return True
        return False

    def is_offscreen(self):
        return all(wall.is_offscreen() for wall in self.walls)


class Game:  # Главный класс, управляющий всей игрой
    def __init__(self):
        self.config = Config()
        pygame.init()

        # Настройки окна
        game_settings = self.config.get('game_settings')
        self.width = game_settings.get('window_width', 600)
        self.height = game_settings.get('window_height', 500)
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Flappy Bird')

        # Частота кадров
        self.clock = pygame.time.Clock()
        self.fps = game_settings.get('fps', 60)

        # Загрузка фона
        self.bg = pygame.image.load('bg.jpg').convert()
        self.bg = pygame.transform.scale(self.bg, (self.width, self.height))

        # Игровые объекты
        bird_config = self.config.get('bird_settings')
        start_x = bird_config.get('start_x', 100)
        start_y = bird_config.get('start_y', self.height // 2)

        self.bird = Bird(start_x, start_y, self.config)
        self.wall_pairs = []

        # Таймер для создания стен
        wall_config = self.config.get('wall_settings')
        spawn_interval = wall_config.get('spawn_interval', 1500)

        self.spawn_wall_event = pygame.USEREVENT
        pygame.time.set_timer(self.spawn_wall_event, spawn_interval)

        # Состояние игры
        self.game_status = 'game'  # 'game' или 'menu'
        self.score = 0

        # Шрифт
        font_name = game_settings.get("font_name", None)
        font_size = game_settings.get("font_size", 36)
        self.font = pygame.freetype.Font(font_name, font_size)

        # Тексты
        texts = self.config.get("texts")
        self.score_text = texts.get("score_prefix", "Score: ")
        self.game_over_text = texts.get("game_over", "GAME OVER")
        self.restart_text = texts.get("restart_instruction", "Press SPACE to restart")

        # Флаг работы игры
        self.running = True

    def handle_events(self):  # обработка ввода
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if self.game_status == 'game':
                        self.bird.jump()
                    elif self.game_status == 'menu':
                        self.restart_game()

            if event.type == self.spawn_wall_event and self.game_status == 'game':
                self.wall_pairs.append(
                    WallPair(self.width, self.height, self.config)
                )

    def update_game_logic(self):  # обновление логики
        if self.game_status == 'game':
            # Обновление птицы
            self.bird.update()

            # Проверка границ для птицы
            bounds_result = self.bird.check_bounds(self.height)
            if bounds_result == 'bottom':
                self.game_status = 'menu'

            # Обновление и проверка стен
            for wall_pair in self.wall_pairs[:]:
                wall_pair.update()

                # Проверка столкновений
                if wall_pair.check_collisions(self.bird.rect):
                    self.game_status = 'menu'

                # Проверка прохождения
                if wall_pair.check_pass(self.bird.rect):
                    self.score += 1  # +1 за пару стен

                # Удаление стен за экраном
                if wall_pair.is_offscreen():
                    self.wall_pairs.remove(wall_pair)

    def draw(self):
        # Рисование фона
        self.screen.blit(self.bg, (0, 0))

        if self.game_status == 'game':
            # Рисование стен
            for wall_pair in self.wall_pairs:
                wall_pair.draw(self.screen)

            # Рисование птицы
            self.bird.draw(self.screen)

            # Отображение счета
            self.font.render_to(
                self.screen,
                (10, 10),
                f'{self.score_text}{self.score}',
                (255, 255, 255)
            )
        else:
            # Экран проигрыша
            self.font.render_to(
                self.screen,
                (self.width // 2 - 120, self.height // 2 - 50),
                self.game_over_text,
                (255, 0, 0)
            )
            self.font.render_to(
                self.screen,
                (self.width // 2 - 100, self.height // 2),
                f'{self.score_text}{self.score}',
                (255, 255, 255)
            )
            self.font.render_to(
                self.screen,
                (self.width // 2 - 200, self.height // 2 + 50),
                self.restart_text,
                (255, 255, 255)
            )

    def restart_game(self):
        self.game_status = 'game'
        bird_config = self.config.get('bird_settings')
        start_x = bird_config.get('start_x', 100)
        start_y = bird_config.get('start_y', self.height // 2)
        self.bird = Bird(start_x, start_y, self.config)
        self.wall_pairs = []
        self.score = 0

    def run(self):
        while self.running:
            self.handle_events()
            self.update_game_logic()
            self.draw()

            pygame.display.flip()
            self.clock.tick(self.fps)

        pygame.quit()


# Запуск игры
if __name__ == "__main__":
    game = Game()
    game.run()
