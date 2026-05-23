INSERT INTO user_entries (user_id, entry_date, mood, work_hours, sleep_hours, comment)
VALUES
    (123456789, CURRENT_DATE - INTERVAL '0 days',  4, 6.0,  7.5, 'Хороший рабочий день, успел многое'),
    (123456789, CURRENT_DATE - INTERVAL '1 day',   3, 4.5,  6.0, 'Немного устал, голова болит'),
    (123456789, CURRENT_DATE - INTERVAL '2 days',  5, 7.0,  8.0, 'Отличный день! Всё получилось'),
    (123456789, CURRENT_DATE - INTERVAL '3 days',  2, 2.0,  5.5, 'Плохо спал, ничего не успел'),
    (123456789, CURRENT_DATE - INTERVAL '4 days',  4, 5.5,  7.0, NULL),
    (123456789, CURRENT_DATE - INTERVAL '5 days',  3, 3.0,  9.0, 'Выходной, расслаблялся'),
    (123456789, CURRENT_DATE - INTERVAL '6 days',  4, 8.0,  7.5, 'Много работал, но доволен'),
    (123456789, CURRENT_DATE - INTERVAL '8 days',  1, 1.0,  4.5, 'Ужасный день, заболел'),
    (123456789, CURRENT_DATE - INTERVAL '9 days',  2, 0.5, 10.0, 'Болел, весь день спал'),
    (123456789, CURRENT_DATE - INTERVAL '10 days', 3, 4.0,  8.0, 'Постепенно прихожу в норму'),
    (123456789, CURRENT_DATE - INTERVAL '12 days', 5, 6.5,  8.5, 'Прекрасный день, гулял и работал'),
    (123456789, CURRENT_DATE - INTERVAL '15 days', 4, 5.0,  7.0, NULL),
    (123456789, CURRENT_DATE - INTERVAL '18 days', 3, 3.5,  6.5, 'Средненький день'),
    (123456789, CURRENT_DATE - INTERVAL '22 days', 5, 7.0,  8.0, 'Завершил большой проект!'),
    (123456789, CURRENT_DATE - INTERVAL '28 days', 2, 2.0,  5.0, 'Стресс, дедлайн горит')
ON CONFLICT (user_id, entry_date) DO NOTHING;