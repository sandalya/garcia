# SESSION — 2026-04-18 00:46

## Проект
garcia

## Що зробили
Підключили web search в Garcia brain.py — _web_search через Anthropic API web_search_20250305. Пропатчили Ed direct.py — додали BOT_PATHS маппінг і підтримку GarciaBrain.run() для --bot garcia. Пропатчили main.py get_transport передавати bot_name. Підсилили GARCIA_PERSONA інструкцію про обовʼязкові URL. Додали reminder в tool result. Ed тести: foundation PASS/WARN, blush стабільно FAIL — URL з пошуку ведуть на іноземні сайти замість укр магазинів

## Наступний крок
Змінити search query стратегію: для search_products додавати 'site:eva.ua OR site:makeup.com.ua OR site:rozetka.com.ua' або робити окремий пошук по укр магазинах. Також фікс addresses_as_ksyu — Garcia не завжди звертається Ксю. Перевірити що escaped \n патч реально застосувався в brain.py

## Контекст
Garcia brain.py має _web_search з web_search_20250305. Ed direct.py має BOT_PATHS dict і GarciaBrain підтримку. GARCIA_PERSONA має секцію КРИТИЧНО: Посилання на продукти. Тест блок 03_links.json — 2 кейси. Рубрика garcia.py має has_real_links critical criterion
