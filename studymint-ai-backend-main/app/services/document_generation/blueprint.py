from __future__ import annotations

from app.schemas.question_bank import ContentBlueprint


def planned_question_total(blueprint: ContentBlueprint) -> int:
    return sum(category.planned_question_count for category in blueprint.categories)


def normalize_blueprint_counts(blueprint: ContentBlueprint, requested_question_count: int) -> ContentBlueprint:
    """
    Correct off-by-a-few blueprint quota errors without inventing subject matter.

    This only adjusts numeric quotas. Category names and objectives still come
    from the model or supplied source context.
    """
    if not blueprint.categories:
        return blueprint

    current_total = planned_question_total(blueprint)

    if current_total == requested_question_count:
        return blueprint

    categories = list(blueprint.categories)

    if current_total <= 0:
        base, remainder = divmod(requested_question_count, len(categories))
        for index, category in enumerate(categories):
            category.planned_question_count = base + (1 if index < remainder else 0)
        blueprint.categories = categories
        return blueprint

    difference = requested_question_count - current_total
    index = 0

    while difference != 0 and categories:
        category = categories[index % len(categories)]

        if difference > 0:
            category.planned_question_count += 1
            difference -= 1
        elif category.planned_question_count > 0:
            category.planned_question_count -= 1
            difference += 1

        index += 1

    blueprint.categories = categories
    return blueprint


def categories_for_question_range(blueprint: ContentBlueprint, start_number: int, end_number: int) -> list[dict]:
    selected: list[dict] = []
    cursor = 1

    for category in blueprint.categories:
        category_start = cursor
        category_end = cursor + category.planned_question_count - 1
        cursor = category_end + 1

        if category_end < start_number or category_start > end_number:
            continue

        selected.append(
            {
                "name": category.name,
                "learning_objectives": category.learning_objectives,
                "question_numbers": [
                    number
                    for number in range(max(start_number, category_start), min(end_number, category_end) + 1)
                ],
            }
        )

    return selected
