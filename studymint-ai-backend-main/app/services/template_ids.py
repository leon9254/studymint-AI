MAIN_ID = "exam_bundle_2026"
BLUE_CERTIFICATION_ID = "tpl_blue_certification_test_bank"
MAIN_TEMPLATE_IDS = {MAIN_ID}
QUESTION_BANK_TEMPLATE_IDS = {MAIN_ID, BLUE_CERTIFICATION_ID}
DEPRECATED_TEMPLATE_IDS = {"tpl_hesi_exit_exam_bundle_2026"}


def is_main_template(template_id: str | None) -> bool:
    return template_id == MAIN_ID


def is_blue_certification_template(template_id: str | None) -> bool:
    return template_id == BLUE_CERTIFICATION_ID


def is_question_bank_template(template_id: str | None) -> bool:
    return template_id in QUESTION_BANK_TEMPLATE_IDS
