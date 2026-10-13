from app.main import app


def test_d009_learner_and_admin_question_schemas_are_typed_and_answer_safe():
    components = app.openapi()["components"]["schemas"]

    matching_learner = components["MatchingLearnerConfig"]
    assert set(matching_learner["properties"]) == {"left_items", "right_items"}
    reorder_learner = components["ReorderLearnerConfig"]
    assert set(reorder_learner["properties"]) == {"items"}
    answer_key_free = components["AnswerKeyFreeConfig"]
    assert answer_key_free.get("properties", {}) == {}
    assert answer_key_free.get("additionalProperties") is False

    assessment = components["AssessmentResponse"]
    item_schema = assessment["properties"]["questions"]["items"]
    assert "oneOf" in item_schema and "discriminator" in item_schema
    learner_models = [name for name in components if name.startswith("Learner") and name.endswith("Question")]
    for name in learner_models:
        properties = components[name]["properties"]
        assert "reference_answer" not in properties and "correct_pairs" not in properties and "correct_order" not in properties

    for schema_name, expected in (("MatchingConfigInput", {"left_items", "right_items", "correct_pairs"}),
                                  ("ReorderConfigInput", {"items", "correct_order"}),
                                  ("FillBlankConfigInput", {"accepted_answers"})):
        assert set(components[schema_name]["properties"]) == expected

    create_request = components["QuestionCreateRequest"]["properties"]
    assert "config" in create_request
    patch_request = components["QuestionPatchRequest"]["properties"]
    assert "type" not in patch_request
    admin_question = components["QuestionAdminResponse"]["properties"]["config"]
    assert "anyOf" in admin_question

    paths = app.openapi()["paths"]
    for path, response_schema in (("/api/v1/admin/lessons", "LessonAdminPageResponse"),
                                  ("/api/v1/admin/assessments", "AssessmentAdminPageResponse")):
        operation = paths[path]["get"]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(response_schema)
        params = {param["name"]: param for param in operation["parameters"]}
        assert params["page"]["schema"]["default"] == 1
        assert params["page"]["schema"]["minimum"] == 1
        assert params["page_size"]["schema"]["default"] == 20
        assert params["page_size"]["schema"]["maximum"] == 100
