---
project: garcia
updated: 2026-04-23
---

# HOT — Garcia (beauty assistant)

## Now

Бот функціонально стабільний. Ксю користується, дає позитивний фідбек (не такий емоційний як про Еббі, але теплий). Поточна сесія — міграція на триярусну пам'ять проекту, більше нічого не чіпаємо.

## Last done

**2026-04-23** — Ініціалізовано HOT/WARM/COLD/MEMORY через `chkp --init garcia`. Зареєстровано в `meta/chkp/projects.yaml`. До цього — рутинне використання без активного дев-циклу.

## Next

1. Провести першу робочу сесію з новою пам'яттю — буде зрозуміло що саме потрібно покращити на основі реального досвіду Ксю.
2. Мігрувати Abby-v2 — останній бот у цій сесії.

## Blockers

Немає.

## Active branches

- **garcia-репо** (`main`): стан гілки — уточнити (`cd garcia && git status`).

## Open questions

- Що конкретно покращити щоб Ксю була у захваті як від Еббі? Наразі немає конкретного фідбеку — з'явиться в процесі використання.

## Reminders

- Workspace: `/home/sashok/.openclaw/workspace/garcia/`
- Перед тестуванням бота — `journalctl -u garcia -f` ДО надсилання повідомлення
- Персона: Penelope Garcia з Criminal Minds, звертається до Ксю як "Ксю"
- Фото від Ксю автоматично зберігаються у `garcia/data/references/`
- API keys маскувати до 4 символів
- Checkpoint: `chkp garcia "done" "next" "context"`
