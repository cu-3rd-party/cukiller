from collections.abc import Iterable
from textwrap import dedent
from typing import Any

_TEXTS: dict[str, str] = {
    # Common
    "common.private_only": "Этот бот работает только в личных сообщениях",
    "common.user_missing": "Не удалось определить пользователя",
    "common.queue_joined": "Вы были помещены в резерв, ожидайте новую миссию...",
    "common.exit_cooldown": "Недавно вы вышли из «Операции». Доступ будет выдан спустя {until}",
    "common.unknown": "Неизвестно",
    "common.username_unknown": "не указан",
    # Score directions
    "score.lost": "потеряли",
    "score.gained": "получили",
    # Buttons / labels
    "buttons.back": "Назад",
    "buttons.cancel": "Отмена",
    "buttons.confirm": "Подтвердить",
    "buttons.confirm_yes": "Да",
    "buttons.no_back": "Нет, назад",
    "buttons.deny": "Нет, спасибо",
    "buttons.send": "Отправить",
    "buttons.restart": "Начать заново",
    "buttons.edit": "Редактировать",
    "buttons.add_more": "Добавить ещё поля",
    "buttons.send_to_moderation": "Отправить на внутреннюю проверку",
    "buttons.profile": "Мое досье",
    "buttons.rules": "Правила",
    "buttons.rules_gameplay": "Игровой процесс",
    "buttons.rules_profile": "Оформление досье",
    "buttons.join_game": "Присоединиться к «Операции»",
    "buttons.leave_game": "Выйти из «Операции»",
    "buttons.get_target": "Получить цель",
    "buttons.was_killed": "Меня раскрыли",
    "buttons.surrender": "Отказаться от цели",
    "buttons.i_killed": "Цель раскрыта",
    "buttons.write_report": "Написать репорт",
    "buttons.open_profile": "Открыть досье",
    "buttons.discussion": "Перейти в чат обсуждения",
    "buttons.next_game": "Когда следующая «Операция»?",
    "buttons.hug_yes": "Да",
    "buttons.hug_no": "Нет",
    "buttons.profile_photo": "Фото досье",
    "buttons.profile_name": "Фамилия и имя",
    "buttons.profile_family_name": "Фамилия",
    "buttons.profile_given_name": "Имя",
    "buttons.profile_academic": "Обучение",
    "buttons.profile_description": "Описание",
    "buttons.cancel_text": "Отмена",
    "buttons.continue": "Продолжить",
    # Main menu
    "main_menu.title": "Главное меню\n",
    "main_menu.rating": "Ваш текущий рейтинг: <b>{user_rating}</b>\n",
    "main_menu.exit_cooldown": (
        " Недавно вы вышли из «Операции». Доступ будет выдан через: <b>{exit_cooldown_until}</b>\n"
    ),
    "main_menu.waiting_victim_confirm": "Запрошено подтверждение раскрытия у второй стороны, ожидайте...",
    "main_menu.waiting_kill_confirm": "Инициировано расследование по вашей цели, ожидаем проверку контрагентов...",
    "main_menu.queue_stats": (
        "Вы находитесь в ожидании новой цели, текущая:\n"
        "Количество агентов контрразведки: <b>{killers_queue_length}</b>\n"
        "Количество потенциальных целей: <b>{victims_queue_length}</b>"
    ),
    "main_menu.target_label": "Ваша цель: {target_name_trimmed}",
    "main_menu.target_info_title": "Информация о цели",
    "main_menu.target_name": "\nФамилия и имя: <b>{target_name}</b>\n",
    "main_menu.target_advanced_info": "{target_advanced_info}",
    # Registration
    "registration.welcome": "Привет, новобранец! Изучи правила оформления профиля, укажи фамилию и имя и заполни свои данные",
    "registration.ask_family_name": "Введи свою фамилию:",
    "registration.ask_given_name": "Введи своё имя:",
    "registration.ask_type": "Выбери тип обучения:",
    "registration.ask_course": "Выбери курс:",
    "registration.ask_group": "Выбери свой поток:",
    "registration.ask_photo": "Теперь отправь фото:",
    "registration.ask_about": "Расскажи о себе:",
    "registration.ask_hugging": 'Разрешено ли вас обнимать при "раскрытии"?',
    "registration.confirm_title": "Проверь данные и отправь на проверку:",
    "registration.confirm.family_name": "<b>Фамилия:</b> {family_name}",
    "registration.confirm.given_name": "<b>Имя:</b> {given_name}",
    "registration.confirm.type": "<b>Тип:</b> {course_type_label}",
    "registration.confirm.course": "<b>Курс:</b> {course_number}",
    "registration.confirm.group": "<b>Поток:</b> {group_name}",
    "registration.confirm.about": "<b>О себе:</b>\n{about}",
    "registration.confirm.hugging": "<b>Объятия при раскрытии:</b> {allow_hugging_on_kill_label}",
    "registration.confirm.photo_attached": "Фото прикреплено",
    "registration.photo_required": "Пожалуйста, отправь фото",
    "registration.submitted": "Твое досье отправлено! Ожидай результаты внутреннего расследования",
    "registration.pending": "Главное, в ходе следственных действий не выйти на самих себя. Твое досье проходит проверку, оперативно сообщим результат",
    # Participation
    "participation.prompt": "Начинается новая «Операция». Вы в деле?",
    "participation.confirm_yes": "Принять приглашение",
    "participation.confirm_no": "Это слишком опасно...",
    # Kill confirmation
    "kills.player_notified": (
        "Агент раскрыт! Все агенты подтвердили нейтрализацию\n\nВы {score_direction} <b>{points}</b> очков рейтинга"
    ),
    "kills.chat_notified": (
        "<b>{killer}</b> раскрыл <b>{victim}</b>\n\n"
        "Новый рейтинг {killer_name}: {killer_rating}({killer_delta})\n"
        "Новый рейтинг {victim_name}: {victim_rating}({victim_delta})\n"
    ),
    "kills.victim_confirm_prompt": "Вы уверены что хотите подтвердить, что вас раскрыли?",
    "kills.victim_double_confirm_prompt": "Контрагент утверждает, что он вас раскрыл. Это правда?",
    "kills.victim_confirm_button": "Да, меня раскрыли",
    "kills.victim_deny_button": "Провокация! Я все еще в тени",
    "kills.killer_confirm_prompt": "Контрольный вопрос: вы раскрыли агента?",
    "kills.killer_double_confirm_prompt": "По версии цели, она была скомпрометирована. Подтвердите",
    "kills.killer_confirm_button": "Цель раскрыта",
    "kills.killer_deny_button": "Дезинформация. Цель под наблюдением",
    # Reroll
    "reroll.player_notified": (
        "Доказательств нет. Но под прикрытием скрывался агент... Цель снята\n\nВы {score_direction} <b>{points}</b> очков рейтинга"
    ),
    "reroll.chat_notified": (
        "<b>{killer}</b> {reason} <b>{victim}</b>\n\n"
        "Новый MMR {killer_name}: {killer_rating}({killer_delta})\n"
        "Новый MMR {victim_name}: {victim_rating}({victim_delta})\n"
    ),
    "reroll.prompt": "Вы уверены что хотите заменить цель?",
    "reroll.confirm": "Да",
    "reroll.cancel": "Нет, назад",
    # Leave game
    "leave.prompt": (
        "Вы уверены, что хотите покинуть операцию?\n"
        "Результат будет эквивалентен раскрытию агента. Следующая активация, не раньше чем через 7 дней"
    ),
    "leave.confirm": "Подтвердить",
    "leave.cancel": "Отменить",
    # leave.killer_notification
    "leave.penalty_changed": "Рейтинг изменился на {penalty}",
    "leave.penalty_unchanged": "Рейтинг не изменился",
    "leave.result": (
        "Вы вышли из игры и стали NPC с богатым прошлым. Но бывших не бывает... {penalty_text}\nВернуться можно после недели ожидания"
    ),
    # Matchmaking
    "matchmaking.admin_log": (
        "Найдено совпадение: {killer} vs {victim} (сходство: {quality:.2f}), создан KillEvent id={kill_event_id}"
    ),
    "matchmaking.killer_message": "Назначена новая цель, изучите досье",
    # Kill timeout
    "timeout.victim": "Вы скрывались {days} дней. Ваш след потерян, контрагент не раскрыл вас",
    "timeout.killer": "Ты зашёл слишком далеко... След оборвался, за {days} дней цель успела скрыться",
    "timeout.discussion": "<b>{killer}</b> не раскрыл <b>{victim}</b> за {days} дней",
    # Ban
    "ban.user_notification": (
        "Вы были забанены. Не пытайтесь продолжить взаимодействие с ботом, это бесполезно"
        "Если считаете что это ошибка, то свяжитесь с администрацией"
    ),
    "ban.admin_notification": 'Игрок {user} был забанен по причине "{reason}"',
    "ban.result": "Пользователь забанен, удалено килл-ивентов: {removed_events}",
    # Admin commands / stats / flows
    "admin.command.start": "Начать работу с ботом",
    "admin.command.stats": "Получить краткую статистику по боту",
    "admin.command.creategame": "Создать новую «Операцию»",
    "admin.command.editgame": "Посмотреть список всех «Операций»",
    "admin.command.server_time": "Получить текущее время на сервере",
    "admin.stats.with_game": (
        "Оперативная сводка\n\n"
        "<b>Операция: {game_name}</b>\n"
        "Продолжительность с начала: {duration}\n"
        "\n"
        "<b>Топ по рейтингу:</b>\n"
        "{rating_top}\n"
        "\n"
        "<b>Лучшая раскрываемость:</b>\n"
        "{killers_top}\n"
        "\n"
        "<b>Агенты, чаще попадавшие под раскрытие</b>\n"
        "{victims_top}"
    ),
    "admin.stats.no_game": (
        "Держи краткую статистику по боту\n\n"
        "В базе данных сейчас находится {user_count} уникальных пользователей\n"
        "Из них {confirmed_count} имеют подтвержденные профили, что составляет {confirmed_percent:.1f}%\n"
        "Сейчас игра <b>не идет</b>\n"
        "\nДругие статистики будут добавляться по ходу дела, хозяин"
    ),
    "admin.notify_new_game": "Внимание, {mention}!!",
    "admin.game_created_alert": "Новая игра создана. Дата создания: {creation_date}",
    "admin.creategame.ask_name": "Ну вот ты хочешь начать новую игру, как назовем ее?",
    "admin.creategame.confirm": "Ну в принципе я получил все что мне надо было, стартуем?",
    "admin.creategame.confirm_yes": "Да, погнали",
    "admin.creategame.confirm_no": "Нет, назад",
    "admin.creategame.already_running": (
        "Ты уверен, что хочешь начать новую игру, не закончив старую?\n\n"
        "Даже если уверен, то ты меня не научил так делать, так "
        "что начала закончи текущую активную игру\n"
        "Для этого можешь воспользоваться /editgame\n"
    ),
    "admin.server_time": "Сейчас на сервере: {server_time}",
    "admin.game_stage.finished": "Завершена",
    "admin.game_stage.started": "Начата",
    "admin.game_stage.error": "err",
    "admin.editgame.select_prompt": "Выбери, какую игру хочешь изменить:",
    "admin.editgame.what_next": "Ну и что с ней делать будем?",
    "admin.editgame.game_title": "Игра {game_name}",
    "admin.editgame.end_game": "Закончить игру",
    "admin.editgame.show_info": "Посмотреть информацию",
    "admin.editgame.back": "Назад",
    "admin.editgame.confirm_end": "Вы уверены что хотите завершить активную игру?",
    "admin.game_selected": "Вы выбрали игру {item_id}",
    "admin.no_active_games": "Сейчас нет активных игр чтобы завершать",
    "admin.game_finished": "Игра успешно завершена\nБот уходит на перезагрузку",
    "admin.ban.ask_args": "Укажи tg_id пользователя и причину: /ban <tg_id> <reason>",
    "admin.ban.tg_id_must_be_int": "tg_id должен быть числом",
    "admin.ban.user_not_found": "Такого пользователя нет в базе данных",
    "admin.game_info": (
        'Информация об игре "{game_name}" с айди {game_id}\n\n'
        "Начало игры: {start_date}\n"
        "Конец игры: {end_date}\n"
        "\nКоличество участников: <b>{participants_count}</b>\n"
    ),
    "admin.game_credits": (
        "Игра <b>{name}</b> закончилась!\n"
        "Она продлилась {duration}\n"
        "\n"
        "<b>Топ по рейтингу:</b>\n"
        "{rating_top}\n"
        "\n"
        "<b>Топ по раскрытиям:</b>\n"
        "{killers_top}\n"
        "\n"
        "<b>Самые часто раскрываемые агенты:</b>\n"
        "{victims_top}\n"
        "\n"
        "{personal_stats}"
    ),
    "admin.personal_stats": (
        "<b>Ваша статистика:</b>\n"
        "Ваш рейтинг к концу игры: <b>{rating}</b>\n"
        "Ваш К/Д: <b>{kills}/{deaths}</b>\n"
        "Логи раскрытиев:\n"
        "{log}"
    ),
    "admin.personal_stats.empty": "Нет данных",
    # Profile moderation
    "moderation.request_already_processed": "Эта заявка уже обработана",
    "moderation.reason_timeout": "Время на указание причины истекло",
    "moderation.reason_saved": "Причина сохранена",
    "moderation.noop": "Никаких действий не требуется, это выключенная кнопка, не видно?",
    "moderation.no_rights": "У вас нет прав для модерации профилей.",
    "moderation.invalid_payload": "Invalid payload",
    "moderation.request_not_found": "Запрос не найден",
    "moderation.request_done": "Заявка уже обработана",
    "moderation.confirmed_alert": "Профиль подтвержден",
    "moderation.denied_alert": "Профиль отклонен",
    "moderation.confirm_notify_new": "Вы прошли проверку. Покрутите рычаги. Посмотрите, что будет",
    "moderation.confirm_notify_update": "Информацию в досье обновили",
    "moderation.notify_reason": (
        "Укажи причину отклонения заявки.\n"
        "ID заявки: {pending_id}\n"
        "Ответь на это сообщение текстом причины или словом None"
    ),
    "moderation.cannot_notify_user": "Не удалось отправить уведомление пользователю {user_id}: {error}",
    "moderation.reason_missing_pending": "Не удалось определить заявку. Ответь на сообщение с ID заявки",
    "moderation.pending_not_found": "Заявка не найдена",
    "moderation.reason_empty": "Пришли текст причины или слово None",
    "moderation.user_denied_new": "Заявка не прошла внутреннюю проверку. Закон — он один для всех",
    "moderation.user_denied_new_reason": "Заявка не прошла внутреннюю проверку, следователь передал сообщение: {reason}",
    "moderation.user_denied_update": "Ваши изменения не соответствуют нашим правилам. Закон — он один для всех",
    "moderation.user_denied_update_reason": "Попытка засчитана, но правила строже. Ваши изменения отклонены. Причина: {reason}.",
    "moderation.status_confirmed": "✅ Подтверждено {moderator}",
    "moderation.status_denied_waiting": "❌ Отклонено {moderator} (ожидаем причину)",
    "moderation.status_denied": "❌ Отклонено {moderator} {reason_part}",
    "moderation.ask_reason_placeholder": "(без причины)",
    "moderation.ask_reason_prefix": "по причине {reason}",
    "moderation.reason_saved_status": "Причина: {reason}",
    "moderation.new_profile_body": (
        "<b>Новый профиль:</b>\n\n"
        "<b>ID заявки:</b> {pending_id}\n"
        "<b>Фамилия:</b> {family_name}\n"
        "<b>Имя:</b> {given_name}\n"
        "<b>Полное имя:</b> {full_name}\n"
        "<b>Тип:</b> {type}\n"
        "<b>Курс:</b> {course_number}\n"
        "<b>Поток:</b> {group_name}\n"
        "<b>О себе:</b> {about_user}\n"
        "<b>Объятия при раскрытии:</b> {allow_hugging_on_kill}\n"
        "<b>Username:</b> @{submitted_username}\n"
        "<b>ID:</b> {user_id}"
    ),
    "moderation.change_header": "<b>Изменение профиля:</b>",
    "moderation.change_meta_id": "<b>ID заявки:</b> {pending_id}",
    "moderation.change_meta_user_id": "<b>ID:</b> {user_id}",
    "moderation.change_meta_username": "<b>Username:</b> @{username}",
    "moderation.change_photo": "<b>{field_label}:</b> обновлено",
    "moderation.change_line": "<b>{field_label}:</b>\n— было: {old_value}\n— стало: {new_value}",
    # Profile editing / viewing
    "profile.toggle_hugs_updated": ("Изменения применены. Профиль агента обновлён и снова отображается в системе"),
    "profile.no_changes": "Нет изменений для отправки",
    "profile.change_sent": "Правки переданы на внутреннюю проверку. Пока активна предыдущая версия профиля",
    "profile.changes_empty": "Изменения пока не добавлены. Добавьте поля и вернитесь к подтверждению",
    "profile.changes_title": "<b>Изменения:</b>",
    "profile.photo_will_be_updated": "<b>{field_label}:</b> фото будет обновлено",
    "profile.change_arrow": "<b>{field_label}:</b> {old_value} -> {new_value}",
    "profile.draft_title": "<b>Черновик досье:</b>\n",
    "profile.draft_body": (
        "Фамилия: <b>{family_name}</b>\n"
        "Имя: <b>{given_name}</b>\n"
        "Тип: {type_value}\n"
        "Курс: {course_value}\n"
        "Поток: {group_value}\n"
        "О себе: {about_value}\n"
        "Объятия при раскрытии: {hugging_value}"
    ),
    "profile.edit_prompt": "Что хотите изменить?",
    "profile.ask_type": "Выбери тип обучения:",
    "profile.ask_course": "Выбери курс:",
    "profile.ask_group": "Выбери свой поток:",
    "profile.ask_family_name": "Введите изменённую фамилию:",
    "profile.ask_given_name": "Введите изменённое имя:",
    "profile.ask_about": "Введите измененное описание:",
    "profile.ask_photo": "Отправь мне новое фото:",
    "profile.hugs_label": "Объятия при раскрытии: {hugs_allowed_label}",
    "profile.preview_changes": "\n{changes_preview}",
    "profile.add_more_fields": "Добавить ещё поля",
    "profile.send_to_moderation": "Отправить на проверку",
    "profile.no_user_found": "Не удалось найти пользователя",
    "profile.hugs_allowed_yes": "разрешены",
    "profile.hugs_allowed_no": "запрещены",
    "profile.name_line": "\nФамилия: <b>{family_name}</b>\nИмя: <b>{given_name}</b>\n",
    "profile.family_name_required": "Профиль временно заблокирован. Укажи фамилию и отправь досье на проверку — после подтверждения доступ восстановится",
    # Matchmaking participation dialog
    "participation.get_target": "Получить цель",
    # Rules
    "rules.body": """
<b><u>Формальные правила игры</u></b>

<b>Правило 0: <i>Не будь мудаком</i></b>
<i>Правила не могут предусмотреть все возможные ситуации.</i>
Администрация имеет право трактовать правила и принимать решения в спорных или неописанных случаях, чтобы сохранить <b>безопасность</b> и <b>честность</b> игры.

<b>0.1. Умышленная порча игрового процесса</b>
<b>Запрещены</b> действия, совершаемые с целью <i>испортить игру другим участникам</i>, даже если нарушитель не получает прямой выгоды:
• срыв раскрытий;
• провокации;
• целенаправленное создание конфликтов;
• саботаж;
• систематическое мешательство;
• спам или флуд по игре;
• намеренное затягивание подтверждений и т. п.
<i>Администрация вправе применять это правило в исключительных случаях по своему усмотрению.</i>

<b>Правило 1: Безопасность и границы</b>

<b>1.1.</b> <i>Уважение личных границ — обязательное условие игры.</i>

<b>1.2.</b> <b>Запрещены:</b> преследование, физическое или психологическое давление, угрозы, шантаж, навязчивые действия, «выкручивание» согласия и прочее.

<b>1.3.</b> <b>Запрещено:</b> блокировать проход, удерживать человека, хватать вещи, одежду или рюкзак, провоцировать падение, толкаться.

<b>1.4.</b> <b>Запрещено</b> проникновение в <i>закрытые зоны</i> (служебные помещения, закрытые комнаты или кабинеты, зоны «только для сотрудников» и т. п.).

<b>1.5. Запрещённые зоны и ситуации для раскрытия:</b>
• туалеты и душевые;
• жилые комнаты в общежитии <i>без явного приглашения</i>;
• <b>во время сна</b>;
• на занятиях, лекциях и экзаменах;
• в ситуациях, где человек явно <i>занят или уязвим</i> (медпункт, оказание помощи другому, эвакуация и т. п.).

<b>Правило 2: Нечестная игра</b>

<b>2.1.</b> <b>Запрещено</b> получать игровое преимущество с помощью:
• использования стороннего ПО, скриптов, ботов или автокликеров;
• эксплуатации уязвимостей, багов и недочётов механик или бота;
• подмены личности, выдачи себя за другого, создания фальшивых аккаунтов;
• подделки доказательств, договорных «сливов», умышленной дезинформации администрации или участников.

<b>2.2.</b> Если вы нашли баг — <i>отлично</i>, отправьте баг-репорт администрации.

<b>Правило 3: Принцип разрешённого</b>
<b>Всё, что не запрещено, разрешено</b>, при условии что это не нарушает правила и не противоречит <i>здравому смыслу</i>!

<b>Правило 4: Мониторинг и решения администрации</b>
Администрация может запрашивать пояснения, проверять спорные ситуации и применять <b>санкции</b>.

<b>Санкции</b>
Администрация может применить следующие меры:
1. Предупреждение или требование (например, об изменении профиля).
2. Снижение рейтинга игрока.
3. Откат действия (например, раскрытия).
4. Запрет участия в конкретной игре.
5. Удаление профиля.
6. Бан.

<i>И помни:</i> <b>Большой брат следит за тобой.</b>
<i>Приятной игры!</i>
""",
    "rules.profile": """
<b>Правила оформления досье (профиля)</b>

<b>1. Обязательные поля</b>
В досье обязательно нужно указать:
• <b><i>настоящее имя</i></b>;
• <b><i>актуальный курс и поток</i></b>.
• <b><i>актуальное фото (подробнее в п2)</i></b>.

<b>2. Фото</b>
2.1. Фото должно быть <b>только вашим</b>.
2.2. На фото должно быть <i>отчётливо видно лицо</i>.
2.3. Присутствие <i>посторонних людей</i> <u>нежелательно</u>.
2.4. <b>Запрещены</b>: чужие фотографии, мемы вместо лица, а также изображения, <i>вводящие в заблуждение</i>.

<b>3. Раздел «О себе»</b>
<b>Запрещены</b> оскорбления, унижения, дискриминационные высказывания, травля, угрозы и любой контент, <i>нарушающий правила университета или законодательство</i>.

<i>Администрация вправе</i> потребовать изменить профиль, отклонить заявку на регистрацию, отказать во внесении изменений в профиль, а в крайнем случае — <b>удалить профиль</b>.
""",
    "rules.game": """
<b>Игровой процесс</b>

<b>Термины</b>
• <b>Операция</b> — игровой раунд (период времени), в котором ведётся охота и идёт подсчёт очков.  
• <b>Досье</b> — профиль игрока в боте: имя, фото, группа и прочие данные.  
• <b>Агент</b> — любой игрок.  
• <b>Шпион</b> — агент, который в данный момент преследует назначенную цель.  
• <b>Контрагент</b> (цель) — агент, которого должен раскрыть конкретный шпион.  
• <b>Раскрытие</b> — успешное выполнение действия, фиксируемое в боте: шпион «снимает» свою цель по правилам ниже.

<b>Цель игры</b>
За время <b>Операции</b>:  
1) сделать как можно больше <b>раскрытий</b>;  
2) как можно реже быть <b>раскрытым</b> другими.

<b>Локация</b>
<b>Раскрытия</b> разрешены <i>только</i> на территории <b>Центрального университета</b>: кампус и/или общежитие.

<b>Как это работает (основной цикл)</b>
1) В начале <b>Операции</b> бот выдаёт каждому агенту <b>цель</b> (контрагента).  
2) Каждый игрок одновременно является:  
• <b>шпионом</b> (охотится на свою цель);  
• <b>целью</b> (за ним охотится другой агент).  
3) После успешного <b>раскрытия</b> бот:  
• начисляет очки <b>шпиону</b> и снимает очки с <b>цели</b>;  
• выдаёт <b>шпиону</b> новую цель;  
• <b>контрагент</b> сохраняет свою цель.

<b>Правила раскрытия</b>
1) <b>Уважение личных границ</b>  
Если в профиле агента указано, что <b>объятия запрещены</b>, необходимо <i>строго</i> следовать этому правилу.  
Также не переходите личные границы при выслеживании цели.  

2) <b>Условие «без свидетелей»</b>  
Раскрытие засчитывается, если в момент попытки рядом <b>нет свидетелей</b>.  

3) <b>Действие раскрытия</b>  
Шпион подходит к цели и выполняет действие: <b>касание плеча</b> или <b>объятие</b>,  
после чего произносит фразу, например:  
<i>«Ничего личного — я тебя раскрыл»</i>.  

4) <b>Фиксация в боте</b>  
<b>Шпион</b> и <b>цель</b> должны в боте нажать соответствующие кнопки <b>подтверждения</b>, либо <b>оспорить</b> раскрытие.

<b>Что происходит после раскрытия</b>
Текущая механика <b>«Бесконечная цепочка»</b>:  
• <b>шпион</b> получает очки и новую цель;  
• <b>раскрытая цель</b> остаётся в игре, но получает <b>штраф</b>, при этом её собственная цель остаётся <i>прежней</i>.

<b>Спорные ситуации</b>
<b>Цель</b> может <b>оспорить</b> раскрытие в случаях:  
1) во время раскрытия в зоне видимости находились <b>свидетели</b>;  
2) не было прямого контакта со <b>шпионом</b>, то есть вас <b>не коснулись</b>.

<b>Механики</b>
• Подбор цели происходит на основе вашего <b>рейтинга</b> и дополнительных <i>скрытых характеристик</i>.  
• <b>Штраф</b> и <b>награда</b> рассчитываются с учётом количества сыгранных раундов, рейтинга цели и шпиона; принцип похож на рейтинг <b>Эло</b> (например, в шахматах или го).
""",
}

_TEXT_LISTS: dict[str, Iterable[str]] = {
    "reroll.fail_reasons": (
        "переоценил свои аналитические способности, чтобы раскрыть",
        "прекратил работу по цели",
        "признал, что имеет недостаточно квалификации, чтоб раскрыть",
        "не смог раскрыть цель, маскировка сработала",
    ),
    "leave.killer_notification": (
        "Цель вышла из игры. «Чистая работа», — подумал Штирлиц",
        "Цель вышла ровно в момент проверки. «Совпадений не бывает», — подумал Штирлиц",
        "Цель вышла, не попрощавшись. «Сдалась», — подумал Штирлиц",
    ),
}

PROFILE_FIELD_LABELS: dict[str, str] = {
    "family_name": "Фамилия",
    "given_name": "Имя",
    "name": "Фамилия и имя",
    "type": "Тип",
    "course_number": "Курс",
    "group_name": "Поток",
    "about_user": "О себе",
    "photo": "Фото",
    "allow_hugging_on_kill": "Объятия при раскрытии",
}


def _prepare(value: str) -> str:
    return dedent(value)


def get(key: str) -> str:
    try:
        return _prepare(_TEXTS[key])
    except KeyError as exc:
        raise KeyError(f"Неизвестный ключ: {key}") from exc


def render(key: str, **kwargs: Any) -> str:
    return get(key).format(**kwargs)


def get_list(key: str) -> tuple[str, ...]:
    try:
        values = _TEXT_LISTS[key]
    except KeyError as exc:
        raise KeyError(f"Неизвестный ключ: {key}") from exc
    return tuple(values)
