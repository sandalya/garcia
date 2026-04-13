# SESSION — 2026-04-13 13:59

## Проект
garcia

## Що зробили
photo handling повністю працює: media_group буфер, multi-image, timestamp в tmp_path; auto-save референсів під капотом через _maybe_save_references (haiku вирішує save/no)

## Наступний крок
перевірити data/references/ через час щоб побачити що Гарсіа зберігає

## Контекст
save logic: після кожного _vision_reply окремий haiku запит JSON {save,name}; зберігає в garcia/data/references/
