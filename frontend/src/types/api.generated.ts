export interface paths {
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Register */
        post: operations["register_api_v1_auth_register_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login_api_v1_auth_login_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me_api_v1_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Refresh */
        post: operations["refresh_api_v1_auth_refresh_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout_api_v1_auth_logout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout-all": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout All */
        post: operations["logout_all_api_v1_auth_logout_all_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/change-password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["change_password_api_v1_auth_change_password_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password-reset/request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Password Reset Request */
        post: operations["password_reset_request_api_v1_auth_password_reset_request_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password-reset/confirm": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Password Reset Confirm */
        post: operations["password_reset_confirm_api_v1_auth_password_reset_confirm_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Conversation */
        post: operations["create_conversation_api_v1_conversations_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Conversations */
        get: operations["list_conversations_api_v1_me_conversations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Conversation */
        get: operations["get_conversation_api_v1_conversations__conversation_id__get"];
        put?: never;
        post?: never;
        /** Delete Conversation */
        delete: operations["delete_conversation_api_v1_conversations__conversation_id__delete"];
        options?: never;
        head?: never;
        /** Rename Conversation */
        patch: operations["rename_conversation_api_v1_conversations__conversation_id__patch"];
        trace?: never;
    };
    "/api/v1/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Message History */
        get: operations["message_history_api_v1_conversations__conversation_id__messages_get"];
        put?: never;
        /** Send Message */
        post: operations["send_message_api_v1_conversations__conversation_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/messages/{assistant_message_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Message */
        post: operations["retry_message_api_v1_messages__assistant_message_id__retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/dashboard": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Dashboard */
        get: operations["dashboard_api_v1_me_dashboard_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pronunciation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Pronunciation */
        get: operations["pronunciation_api_v1_pronunciation_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/pronunciation/{section_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Pronunciation Complete */
        post: operations["pronunciation_complete_api_v1_pronunciation__section_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/lessons/{lesson_id}/theory/vocabulary/{lesson_vocabulary_id}/view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Vocabulary View */
        post: operations["vocabulary_view_api_v1_lessons__lesson_id__theory_vocabulary__lesson_vocabulary_id__view_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/lessons/{lesson_id}/theory/grammar/{lesson_grammar_id}/view": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Grammar View */
        post: operations["grammar_view_api_v1_lessons__lesson_id__theory_grammar__lesson_grammar_id__view_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Progress */
        get: operations["progress_api_v1_me_progress_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/progress/hsk/{hsk_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Hsk Progress */
        get: operations["hsk_progress_api_v1_me_progress_hsk__hsk_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/progress/lessons/{lesson_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lesson Progress */
        get: operations["lesson_progress_api_v1_me_progress_lessons__lesson_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/hsk-levels": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Hsk Levels */
        get: operations["hsk_levels_api_v1_hsk_levels_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/hsk-levels/{hsk_id}/curriculum": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Curriculum */
        get: operations["curriculum_api_v1_hsk_levels__hsk_id__curriculum_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/lessons/{lesson_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lesson */
        get: operations["lesson_api_v1_lessons__lesson_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assessments/{assessment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Assessment */
        get: operations["assessment_api_v1_assessments__assessment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assessments/{assessment_id}/attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start */
        post: operations["start_api_v1_assessments__assessment_id__attempts_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assessment-attempts/{attempt_id}/submit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit */
        post: operations["submit_api_v1_assessment_attempts__attempt_id__submit_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/assessment-attempts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** History */
        get: operations["history_api_v1_me_assessment_attempts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/assessment-attempts/{attempt_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Detail */
        get: operations["detail_api_v1_me_assessment_attempts__attempt_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Documents */
        get: operations["list_documents_api_v1_admin_documents_get"];
        put?: never;
        /** Upload Document */
        post: operations["upload_document_api_v1_admin_documents_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Document Detail */
        get: operations["get_document_detail_api_v1_admin_documents__document_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}/process": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Process Document */
        post: operations["process_document_api_v1_admin_documents__document_id__process_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview Document */
        get: operations["preview_document_api_v1_admin_documents__document_id__preview_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}/approve": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Approve Document */
        post: operations["approve_document_api_v1_admin_documents__document_id__approve_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}/reject": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reject Document */
        post: operations["reject_document_api_v1_admin_documents__document_id__reject_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/documents/{document_id}/knowledge/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Document Knowledge */
        post: operations["retry_document_knowledge_api_v1_admin_documents__document_id__knowledge_retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/hsk-levels": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Hsk Levels */
        get: operations["hsk_levels_api_v1_admin_hsk_levels_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/hsk-levels/{hsk_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Hsk */
        patch: operations["patch_hsk_api_v1_admin_hsk_levels__hsk_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/hsk-levels/{hsk_id}/curriculum": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Curriculum */
        get: operations["get_curriculum_api_v1_admin_hsk_levels__hsk_id__curriculum_get"];
        /** Put Curriculum */
        put: operations["put_curriculum_api_v1_admin_hsk_levels__hsk_id__curriculum_put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Lessons */
        get: operations["lessons_api_v1_admin_lessons_get"];
        put?: never;
        /** Create Lesson */
        post: operations["create_lesson_api_v1_admin_lessons_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Lesson */
        get: operations["get_lesson_api_v1_admin_lessons__lesson_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Lesson */
        patch: operations["patch_lesson_api_v1_admin_lessons__lesson_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish Lesson */
        post: operations["publish_lesson_api_v1_admin_lessons__lesson_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/knowledge/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Lesson Knowledge */
        post: operations["retry_lesson_knowledge_api_v1_admin_lessons__lesson_id__knowledge_retry_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Lesson */
        post: operations["archive_lesson_api_v1_admin_lessons__lesson_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/vocabulary": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Items */
        get: operations["get_items_api_v1_admin_lessons__lesson_id__vocabulary_get"];
        put?: never;
        /** Attach */
        post: operations["attach_api_v1_admin_lessons__lesson_id__vocabulary_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/vocabulary/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Detach */
        delete: operations["detach_api_v1_admin_lessons__lesson_id__vocabulary__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch */
        patch: operations["patch_api_v1_admin_lessons__lesson_id__vocabulary__item_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/grammar": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Items */
        get: operations["get_items_api_v1_admin_lessons__lesson_id__grammar_get"];
        put?: never;
        /** Attach */
        post: operations["attach_api_v1_admin_lessons__lesson_id__grammar_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/lessons/{lesson_id}/grammar/{item_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Detach */
        delete: operations["detach_api_v1_admin_lessons__lesson_id__grammar__item_id__delete"];
        options?: never;
        head?: never;
        /** Patch */
        patch: operations["patch_api_v1_admin_lessons__lesson_id__grammar__item_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/assessments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Assessments */
        get: operations["assessments_api_v1_admin_assessments_get"];
        put?: never;
        /** Create Assessment */
        post: operations["create_assessment_api_v1_admin_assessments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/assessments/generate-draft": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Generate Assessment Draft */
        post: operations["generate_assessment_draft_api_v1_admin_assessments_generate_draft_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Assessment */
        get: operations["get_assessment_api_v1_admin_assessments__assessment_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Assessment */
        patch: operations["patch_assessment_api_v1_admin_assessments__assessment_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}/questions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Questions */
        get: operations["questions_api_v1_admin_assessments__assessment_id__questions_get"];
        put?: never;
        /** Create Question */
        post: operations["create_question_api_v1_admin_assessments__assessment_id__questions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}/questions/{question_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Delete Question */
        delete: operations["delete_question_api_v1_admin_assessments__assessment_id__questions__question_id__delete"];
        options?: never;
        head?: never;
        /** Patch Question */
        patch: operations["patch_question_api_v1_admin_assessments__assessment_id__questions__question_id__patch"];
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}/submit-review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Submit Review */
        post: operations["submit_review_api_v1_admin_assessments__assessment_id__submit_review_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}/publish": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Publish Assessment */
        post: operations["publish_assessment_api_v1_admin_assessments__assessment_id__publish_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/assessments/{assessment_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Assessment */
        post: operations["archive_assessment_api_v1_admin_assessments__assessment_id__archive_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/admin/stats": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stats */
        get: operations["stats_api_v1_admin_stats_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Health
         * @description Report that the backend process is alive.
         */
        get: operations["health_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Readiness
         * @description Report whether the database dependency answers a lightweight probe.
         */
        get: operations["readiness_ready_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AdminCurriculumUnitResponse */
        AdminCurriculumUnitResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Order Index */
            order_index: number;
            /**
             * Unit Type
             * @enum {string}
             */
            unit_type: "LESSON" | "PERIODIC_TEST";
            /** Lesson Id */
            lesson_id: string | null;
            /** Assessment Id */
            assessment_id: string | null;
            /** Lesson Title */
            lesson_title: string | null;
            /** Assessment Title */
            assessment_title: string | null;
        };
        /** AdminHskUserCountResponse */
        AdminHskUserCountResponse: {
            /** Hsk Level */
            hsk_level: number;
            /** Users */
            users: number;
        };
        /** AdminStatsResponse */
        AdminStatsResponse: {
            /** Total Users */
            total_users: number;
            /** Users By Current Hsk */
            users_by_current_hsk: components["schemas"]["AdminHskUserCountResponse"][];
            /** Average Exercise Score */
            average_exercise_score: number | null;
        };
        /** AnswerKeyFreeConfig */
        AnswerKeyFreeConfig: Record<string, never>;
        /** AssessmentAdminPageResponse */
        AssessmentAdminPageResponse: {
            /** Items */
            items: components["schemas"]["AssessmentAdminResponse"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** AssessmentAdminResponse */
        AssessmentAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Type
             * @enum {string}
             */
            type: "LESSON_EXERCISE" | "PERIODIC_TEST";
            /** Lesson Id */
            lesson_id: string | null;
            /** Title */
            title: string;
            /** Description */
            description: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "DRAFT" | "REVIEW" | "PUBLISHED" | "ARCHIVED";
            /** Pass Threshold */
            pass_threshold: number;
            /** Published At */
            published_at: string | null;
        };
        /** AssessmentCreateRequest */
        AssessmentCreateRequest: {
            /**
             * Type
             * @enum {string}
             */
            type: "LESSON_EXERCISE" | "PERIODIC_TEST";
            /** Lesson Id */
            lesson_id?: string | null;
            /** Title */
            title: string;
            /** Description */
            description?: string | null;
            /**
             * Pass Threshold
             * @default 90
             */
            pass_threshold: number;
            /** Lesson Ids */
            lesson_ids?: string[] | null;
            /** Vocabulary Ids */
            vocabulary_ids?: string[] | null;
            /** Grammar Ids */
            grammar_ids?: string[] | null;
        };
        /** AssessmentGenerationDraftResponse */
        AssessmentGenerationDraftResponse: {
            assessment: components["schemas"]["AssessmentAdminResponse"];
            /** Questions */
            questions: components["schemas"]["QuestionAdminResponse"][];
        };
        /** AssessmentPatchRequest */
        AssessmentPatchRequest: {
            /** Title */
            title?: string;
            /** Description */
            description?: string | null;
            /** Pass Threshold */
            pass_threshold?: number;
            /** Lesson Ids */
            lesson_ids?: string[] | null;
            /** Vocabulary Ids */
            vocabulary_ids?: string[] | null;
            /** Grammar Ids */
            grammar_ids?: string[] | null;
        };
        /** AssessmentResponse */
        AssessmentResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Type
             * @enum {string}
             */
            type: "LESSON_EXERCISE" | "PERIODIC_TEST";
            /** Title */
            title: string;
            /** Description */
            description: string | null;
            /** Pass Threshold */
            pass_threshold: number;
            /** Questions */
            questions: (components["schemas"]["LearnerMultipleChoiceQuestion"] | components["schemas"]["LearnerFillBlankQuestion"] | components["schemas"]["LearnerMatchingQuestion"] | components["schemas"]["LearnerReorderQuestion"] | components["schemas"]["LearnerTextQuestion"])[];
        };
        /** AttemptDetailResponse */
        AttemptDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Assessment Id
             * Format: uuid
             */
            assessment_id: string;
            /** Attempt Number */
            attempt_number: number;
            /**
             * Status
             * @enum {string}
             */
            status: "IN_PROGRESS" | "SUBMITTED" | "GRADED" | "GRADING_FAILED";
            /** Score */
            score: number | null;
            /** Passed */
            passed: boolean | null;
            /** Submitted At */
            submitted_at: string | null;
            /** Answers */
            answers: (components["schemas"]["MultipleChoiceAttemptAnswerResult"] | components["schemas"]["FillBlankAttemptAnswerResult"] | components["schemas"]["MatchingAttemptAnswerResult"] | components["schemas"]["ReorderAttemptAnswerResult"] | components["schemas"]["TextAttemptAnswerResult"])[];
        };
        /** AttemptHistoryItem */
        AttemptHistoryItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Assessment Id
             * Format: uuid
             */
            assessment_id: string;
            /** Assessment Title */
            assessment_title: string;
            /**
             * Assessment Type
             * @enum {string}
             */
            assessment_type: "LESSON_EXERCISE" | "PERIODIC_TEST";
            /** Attempt Number */
            attempt_number: number;
            /**
             * Status
             * @enum {string}
             */
            status: "IN_PROGRESS" | "SUBMITTED" | "GRADED" | "GRADING_FAILED";
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
            /** Submitted At */
            submitted_at: string | null;
            /** Score */
            score: number | null;
            /** Passed */
            passed: boolean | null;
        };
        /** AttemptHistoryPage */
        AttemptHistoryPage: {
            /** Items */
            items: components["schemas"]["AttemptHistoryItem"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** AttemptResponse */
        AttemptResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Assessment Id
             * Format: uuid
             */
            assessment_id: string;
            /** Attempt Number */
            attempt_number: number;
            /**
             * Status
             * @enum {string}
             */
            status: "IN_PROGRESS" | "SUBMITTED" | "GRADED" | "GRADING_FAILED";
            /**
             * Started At
             * Format: date-time
             */
            started_at: string;
        };
        /** AttemptSubmissionResponse */
        AttemptSubmissionResponse: {
            /**
             * Attempt Id
             * Format: uuid
             */
            attempt_id: string;
            /**
             * Status
             * @constant
             */
            status: "GRADED";
            /** Score */
            score: number | null;
            /** Passed */
            passed: boolean | null;
        };
        /** Body_upload_document_api_v1_admin_documents_post */
        Body_upload_document_api_v1_admin_documents_post: {
            /** File */
            file: string;
            /** Title */
            title: string;
            /** Source Category */
            source_category: string;
            /** Source Origin */
            source_origin: string;
            /** Source Language */
            source_language: string;
            /** Usage Rights Note */
            usage_rights_note?: string | null;
            /** Domain Allowed */
            domain_allowed: boolean;
        };
        /** CanonicalBlock */
        CanonicalBlock: {
            /** Order */
            order: number;
            /**
             * Content Type
             * @enum {string}
             */
            content_type: "DOCUMENT_TEXT" | "VOCABULARY" | "GRAMMAR" | "LESSON_GENERAL";
            /**
             * Block Kind
             * @enum {string}
             */
            block_kind: "HEADING" | "PARAGRAPH" | "LIST" | "CODE_BLOCK" | "TABLE" | "VOCABULARY_ITEM" | "GRAMMAR_SECTION" | "LESSON_GENERAL";
            /** Text */
            text: string;
            /** Section Path */
            section_path: string[];
            /** Source Locator */
            source_locator: components["schemas"]["PDFPageLocator"] | components["schemas"]["DOCXParagraphLocator"] | components["schemas"]["TextBlockLocator"] | components["schemas"]["MarkdownBlockLocator"] | components["schemas"]["MarkdownListLocator"] | components["schemas"]["DOCXTableLocator"] | components["schemas"]["LessonEntityLocator"];
            /** Structured Data */
            structured_data?: components["schemas"]["EmptyStructuredData"] | components["schemas"]["TableStructuredData"] | components["schemas"]["ListStructuredData"] | components["schemas"]["VocabularyStructuredData"] | components["schemas"]["GrammarStructuredData"];
            metadata?: components["schemas"]["EmptyMetadata"];
        };
        /** ChangePasswordRequest */
        ChangePasswordRequest: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /** CitationResponse */
        CitationResponse: {
            /** Label */
            label: string;
            /**
             * Source Kind
             * @enum {string}
             */
            source_kind: "INTERNAL_CHUNK" | "EXTERNAL_URL";
            /** Title */
            title: string;
            /** Source Type */
            source_type: ("DOCUMENT" | "LESSON") | null;
            /** Section */
            section: string | null;
            /** Page Number */
            page_number: number | null;
            /** Url */
            url: string | null;
            /** Domain */
            domain: string | null;
        };
        /** ConversationCreateRequest */
        ConversationCreateRequest: {
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
        };
        /** ConversationPage */
        ConversationPage: {
            /** Items */
            items: components["schemas"]["ConversationResponse"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** ConversationPatchRequest */
        ConversationPatchRequest: {
            /** Title */
            title: string | null;
        };
        /** ConversationResponse */
        ConversationResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Scope
             * @default LESSON
             * @constant
             */
            scope: "LESSON";
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
            /** Title */
            title: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** CorrectPairInput */
        CorrectPairInput: {
            /** Left Id */
            left_id: string;
            /** Right Id */
            right_id: string;
        };
        /** CurriculumAssessmentSummary */
        CurriculumAssessmentSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Title */
            title: string;
            /**
             * Type
             * @enum {string}
             */
            type: "LESSON_EXERCISE" | "PERIODIC_TEST";
            /**
             * Status
             * @enum {string}
             */
            status: "DRAFT" | "REVIEW" | "PUBLISHED" | "ARCHIVED";
        };
        /** CurriculumLessonSummary */
        CurriculumLessonSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Lesson Number */
            lesson_number: number;
            /** Title */
            title: string;
            /**
             * Status
             * @enum {string}
             */
            status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
        };
        /** CurriculumPutRequest */
        CurriculumPutRequest: {
            /** Units */
            units: components["schemas"]["CurriculumUnitInput"][];
        };
        /** CurriculumResponse */
        CurriculumResponse: {
            hsk: components["schemas"]["HskSummaryResponse"];
            /** Units */
            units: components["schemas"]["UnitProgress"][];
        };
        /** CurriculumUnitInput */
        CurriculumUnitInput: {
            /**
             * Unit Type
             * @enum {string}
             */
            unit_type: "LESSON" | "PERIODIC_TEST";
            /**
             * Target Id
             * Format: uuid
             */
            target_id: string;
            /** Order Index */
            order_index: number;
        };
        /** DOCXParagraphLocator */
        DOCXParagraphLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "DOCX_PARAGRAPH";
            /** Block Index */
            block_index: number;
        };
        /** DOCXTableLocator */
        DOCXTableLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "DOCX_TABLE";
            /** Table Index */
            table_index: number;
            /** Rows */
            rows: components["schemas"]["DOCXTableRowLocator"][];
        };
        /** DOCXTableRowLocator */
        DOCXTableRowLocator: {
            /**
             * Kind
             * @constant
             */
            kind: "DOCX_TABLE_ROW";
            /** Table Index */
            table_index: number;
            /** Row Index */
            row_index: number;
            /** Block Index */
            block_index: number;
        };
        /** DashboardLessonSummary */
        DashboardLessonSummary: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Lesson Number */
            lesson_number: number;
            /** Title */
            title: string;
            /** Description */
            description: string | null;
        };
        /** DashboardResponse */
        DashboardResponse: {
            current_hsk: components["schemas"]["HskSummaryResponse"] | null;
            current_unit: components["schemas"]["UnitProgress"] | null;
            current_lesson: components["schemas"]["DashboardLessonSummary"] | null;
            /** Progress Percentage */
            progress_percentage: number;
            /** Continue Learning */
            continue_learning: (components["schemas"]["PronunciationContinueLearning"] | components["schemas"]["LessonContinueLearning"] | components["schemas"]["PeriodicTestContinueLearning"]) | null;
        };
        /** DocumentAdminDetailResponse */
        DocumentAdminDetailResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /** File Type */
            file_type: string;
            /** Mime Type */
            mime_type: string | null;
            /** File Size Bytes */
            file_size_bytes: number | null;
            /** Title */
            title: string | null;
            /** Source Category */
            source_category: ("CURRICULUM_MATERIAL" | "INTERNAL_AUTHORED") | null;
            /** Source Origin */
            source_origin: string | null;
            /** Source Language */
            source_language: ("vi" | "zh" | "en") | null;
            /** Usage Rights Note */
            usage_rights_note: string | null;
            /**
             * Processing Status
             * @enum {string}
             */
            processing_status: "UPLOADED" | "PROCESSING" | "PREVIEW_READY" | "FAILED";
            /**
             * Review Status
             * @enum {string}
             */
            review_status: "PENDING" | "APPROVED" | "REJECTED";
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Approved At */
            approved_at: string | null;
            /** Knowledge Retry Available */
            knowledge_retry_available: boolean;
        };
        /** DocumentAdminListItemResponse */
        DocumentAdminListItemResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /** File Type */
            file_type: string;
            /** Mime Type */
            mime_type: string | null;
            /** File Size Bytes */
            file_size_bytes: number | null;
            /** Title */
            title: string | null;
            /** Source Category */
            source_category: ("CURRICULUM_MATERIAL" | "INTERNAL_AUTHORED") | null;
            /** Source Origin */
            source_origin: string | null;
            /** Source Language */
            source_language: ("vi" | "zh" | "en") | null;
            /** Usage Rights Note */
            usage_rights_note: string | null;
            /**
             * Processing Status
             * @enum {string}
             */
            processing_status: "UPLOADED" | "PROCESSING" | "PREVIEW_READY" | "FAILED";
            /**
             * Review Status
             * @enum {string}
             */
            review_status: "PENDING" | "APPROVED" | "REJECTED";
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
            /** Approved At */
            approved_at: string | null;
        };
        /** DocumentAdminPageResponse */
        DocumentAdminPageResponse: {
            /** Items */
            items: components["schemas"]["DocumentAdminListItemResponse"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** DocumentProvenance */
        DocumentProvenance: {
            /** Source Origin */
            source_origin: string;
            /** Usage Rights Note */
            usage_rights_note?: string | null;
            /** Original Filename */
            original_filename?: string | null;
        };
        /** DocumentRawIngestionResponse */
        DocumentRawIngestionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Original Filename */
            original_filename: string;
            /** File Type */
            file_type: string;
            /** Mime Type */
            mime_type: string;
            /** File Size Bytes */
            file_size_bytes: number;
            /** Content Hash */
            content_hash: string;
            /** Title */
            title: string;
            /** Source Category */
            source_category: string;
            /** Source Origin */
            source_origin: string;
            /** Source Language */
            source_language: string;
            /** Usage Rights Note */
            usage_rights_note: string | null;
            /** Processing Status */
            processing_status: string;
            /** Review Status */
            review_status: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
        };
        /** EmptyMetadata */
        EmptyMetadata: Record<string, never>;
        /** EmptyStructuredData */
        EmptyStructuredData: Record<string, never>;
        /** FillBlankAnswer */
        FillBlankAnswer: {
            /** Text */
            text: string;
        };
        /** FillBlankAttemptAnswerResult */
        FillBlankAttemptAnswerResult: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Prompt */
            prompt: string;
            /**
             * Grading Status
             * @enum {string}
             */
            grading_status: "PENDING" | "GRADED" | "UNCERTAIN" | "FAILED";
            /** Score */
            score: number | null;
            /** Is Correct */
            is_correct: boolean | null;
            /** Feedback */
            feedback: string | null;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "fill_blank";
            answer: components["schemas"]["FillBlankAnswer"] | null;
            config?: components["schemas"]["ResultFillBlankConfig"] | null;
        };
        /** FillBlankConfigInput */
        FillBlankConfigInput: {
            /** Accepted Answers */
            accepted_answers?: string[];
        };
        /** GrammarAttachRequest */
        GrammarAttachRequest: {
            /**
             * Grammar Id
             * Format: uuid
             */
            grammar_id?: string;
            /** Name */
            name?: string;
            /** Structure */
            structure?: string | null;
            /** Explanation */
            explanation?: string;
            /** Usage */
            usage?: string | null;
            /** Order Index */
            order_index: number;
            /** Note */
            note?: string | null;
            /** Example */
            example?: string | null;
        };
        /** GrammarItemResponse */
        GrammarItemResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Structure */
            structure: string | null;
            /** Explanation */
            explanation: string;
            /** Usage */
            usage: string | null;
        };
        /** GrammarLessonItem */
        GrammarLessonItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Order Index */
            order_index: number;
            /** Note */
            note: string | null;
            /** Example */
            example: string | null;
            item: components["schemas"]["GrammarItemResponse"];
        };
        /** GrammarPatchRequest */
        GrammarPatchRequest: {
            /** Order Index */
            order_index?: number;
            /** Note */
            note?: string | null;
            /** Example */
            example?: string | null;
            /** Name */
            name?: string;
            /** Structure */
            structure?: string | null;
            /** Explanation */
            explanation?: string;
            /** Usage */
            usage?: string | null;
        };
        /** GrammarStructuredData */
        GrammarStructuredData: {
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
            /**
             * Grammar Id
             * Format: uuid
             */
            grammar_id: string;
            /** Name */
            name?: string | null;
            /** Structure */
            structure?: string | null;
            /** Explanation */
            explanation?: string | null;
            /** Usage */
            usage?: string | null;
            /** Example */
            example?: string | null;
            /** Note */
            note?: string | null;
        };
        /** HSKAdminResponse */
        HSKAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Level Number */
            level_number: number;
            /** Title */
            title: string | null;
            /** Description */
            description: string | null;
            /** Order Index */
            order_index: number;
        };
        /** HSKLevelResponse */
        HSKLevelResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Level Number */
            level_number: number;
            /** Title */
            title: string | null;
            /** Description */
            description?: string | null;
            /**
             * State
             * @enum {string}
             */
            state: "LOCKED" | "AVAILABLE" | "COMPLETED";
        };
        /** HSKPatchRequest */
        HSKPatchRequest: {
            /** Title */
            title?: string | null;
            /** Description */
            description?: string | null;
        };
        /** HSKProgressResponse */
        HSKProgressResponse: {
            hsk: components["schemas"]["HskSummaryResponse"];
            /** Units */
            units: components["schemas"]["UnitProgress"][];
            /** Progress Percentage */
            progress_percentage: number;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HskSummaryResponse */
        HskSummaryResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Level Number */
            level_number: number;
            /** Title */
            title: string | null;
        };
        /** LearnerFillBlankQuestion */
        LearnerFillBlankQuestion: {
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Points */
            points: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "fill_blank";
            config: components["schemas"]["AnswerKeyFreeConfig"];
        };
        /** LearnerMatchingQuestion */
        LearnerMatchingQuestion: {
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Points */
            points: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "matching";
            config: components["schemas"]["MatchingLearnerConfig"];
        };
        /** LearnerMultipleChoiceQuestion */
        LearnerMultipleChoiceQuestion: {
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Points */
            points: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "multiple_choice";
            config: components["schemas"]["AnswerKeyFreeConfig"];
            /** Options */
            options: components["schemas"]["LearnerOptionResponse"][];
        };
        /** LearnerOptionResponse */
        LearnerOptionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Option Text */
            option_text: string;
        };
        /** LearnerReorderQuestion */
        LearnerReorderQuestion: {
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Points */
            points: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "reorder_sentence";
            config: components["schemas"]["ReorderLearnerConfig"];
        };
        /** LearnerTextQuestion */
        LearnerTextQuestion: {
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Points */
            points: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "sentence_writing" | "translate_vi_zh" | "translate_zh_vi";
            config: components["schemas"]["AnswerKeyFreeConfig"];
        };
        /** LessonAdminPageResponse */
        LessonAdminPageResponse: {
            /** Items */
            items: components["schemas"]["LessonAdminResponse"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** LessonAdminResponse */
        LessonAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Hsk Level Id
             * Format: uuid
             */
            hsk_level_id: string;
            /** Lesson Number */
            lesson_number: number;
            /** Title */
            title: string;
            /** Description */
            description: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "DRAFT" | "PUBLISHED" | "ARCHIVED";
            /** Published At */
            published_at: string | null;
        };
        /** LessonContentAdminResponse */
        LessonContentAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Order Index */
            order_index: number;
            /** Note */
            note: string | null;
            /** Example */
            example: string | null;
            /** Vocabulary Id */
            vocabulary_id?: string | null;
            /** Grammar Id */
            grammar_id?: string | null;
            /** Hanzi */
            hanzi?: string | null;
            /** Pinyin */
            pinyin?: string | null;
            /** Vietnamese Meaning */
            vietnamese_meaning?: string | null;
            /** Part Of Speech */
            part_of_speech?: string | null;
            /** Name */
            name?: string | null;
            /** Structure */
            structure?: string | null;
            /** Explanation */
            explanation?: string | null;
            /** Usage */
            usage?: string | null;
        };
        /** LessonContinueLearning */
        LessonContinueLearning: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "LESSON";
            /** Section Id */
            section_id?: null;
            /** Code */
            code?: null;
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
            /** Assessment Id */
            assessment_id?: null;
        };
        /** LessonCreateRequest */
        LessonCreateRequest: {
            /**
             * Hsk Level Id
             * Format: uuid
             */
            hsk_level_id: string;
            /** Lesson Number */
            lesson_number: number;
            /** Title */
            title: string;
            /** Description */
            description?: string | null;
        };
        /** LessonEntityLocator */
        LessonEntityLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "LESSON_ENTITY";
            /**
             * Section
             * @enum {string}
             */
            section: "LESSON" | "VOCABULARY" | "GRAMMAR";
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /** Order Index */
            order_index?: number | null;
            /** Fields */
            fields: components["schemas"]["LessonFieldLocator"][];
        };
        /** LessonExerciseGenerationRequest */
        LessonExerciseGenerationRequest: {
            /** Title */
            title?: string | null;
            /** Description */
            description?: string | null;
            /**
             * Pass Threshold
             * @default 90
             */
            pass_threshold: number;
            /** Question Count */
            question_count: number;
            /** Allowed Types */
            allowed_types: ("multiple_choice" | "fill_blank" | "matching" | "reorder_sentence" | "translate_vi_zh" | "translate_zh_vi" | "sentence_writing")[];
            /**
             * Difficulty
             * @enum {string}
             */
            difficulty: "EASY" | "MEDIUM" | "HARD";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "LESSON_EXERCISE";
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
        };
        /** LessonFieldLocator */
        LessonFieldLocator: {
            /**
             * Kind
             * @constant
             */
            kind: "LESSON_FIELD";
            /**
             * Section
             * @enum {string}
             */
            section: "LESSON" | "VOCABULARY" | "GRAMMAR";
            /**
             * Entity Id
             * Format: uuid
             */
            entity_id: string;
            /**
             * Field
             * @enum {string}
             */
            field: "title" | "description" | "hanzi" | "pinyin" | "vietnamese_meaning" | "part_of_speech" | "example" | "note" | "name" | "structure" | "explanation" | "usage";
            /** Order Index */
            order_index?: number | null;
        };
        /** LessonPatchRequest */
        LessonPatchRequest: {
            /** Title */
            title?: string;
            /** Description */
            description?: string | null;
        };
        /** LessonProgressResponse */
        LessonProgressResponse: {
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
            /** Started At */
            started_at: string | null;
            /** Theory Completed At */
            theory_completed_at: string | null;
            /** Completed At */
            completed_at: string | null;
            /** Vocabulary */
            vocabulary: components["schemas"]["TheoryContentProgressResponse"][];
            /** Grammar */
            grammar: components["schemas"]["TheoryContentProgressResponse"][];
        };
        /** LessonProvenance */
        LessonProvenance: Record<string, never>;
        /** LessonResponse */
        LessonResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Hsk Level Id
             * Format: uuid
             */
            hsk_level_id: string;
            /** Lesson Number */
            lesson_number: number;
            /** Title */
            title: string;
            /** Description */
            description: string | null;
            /** Vocabulary */
            vocabulary: components["schemas"]["VocabularyLessonItem"][];
            /** Grammar */
            grammar: components["schemas"]["GrammarLessonItem"][];
            /** Assessment Ids */
            assessment_ids: string[];
        };
        /** ListStructuredData */
        ListStructuredData: {
            /**
             * List Kind
             * @enum {string}
             */
            list_kind: "ordered" | "unordered";
            /** Items */
            items: string[];
        };
        /** LoginRequest */
        LoginRequest: {
            /** Email */
            email: string;
            /** Password */
            password: string;
        };
        /** MarkdownBlockLocator */
        MarkdownBlockLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "MARKDOWN_BLOCK";
            /** Block Index */
            block_index: number;
            /**
             * Block Kind
             * @enum {string}
             */
            block_kind: "HEADING" | "PARAGRAPH" | "CODE_BLOCK" | "LIST_ITEM";
            /** Heading Level */
            heading_level?: number | null;
            /** List Kind */
            list_kind?: ("ordered" | "unordered") | null;
        };
        /** MarkdownListLocator */
        MarkdownListLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "MARKDOWN_LIST";
            /**
             * List Kind
             * @enum {string}
             */
            list_kind: "ordered" | "unordered";
            /** Members */
            members: components["schemas"]["MarkdownBlockLocator"][];
        };
        /** MatchItemResponse */
        MatchItemResponse: {
            /** Id */
            id: string;
            /** Text */
            text: string;
        };
        /** MatchingAnswer */
        MatchingAnswer: {
            /** Pairs */
            pairs: components["schemas"]["MatchingPair"][];
        };
        /** MatchingAttemptAnswerResult */
        MatchingAttemptAnswerResult: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Prompt */
            prompt: string;
            /**
             * Grading Status
             * @enum {string}
             */
            grading_status: "PENDING" | "GRADED" | "UNCERTAIN" | "FAILED";
            /** Score */
            score: number | null;
            /** Is Correct */
            is_correct: boolean | null;
            /** Feedback */
            feedback: string | null;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "matching";
            answer: components["schemas"]["MatchingAnswer"] | null;
            config?: components["schemas"]["ResultMatchingConfig"] | null;
        };
        /** MatchingConfigInput */
        MatchingConfigInput: {
            /** Left Items */
            left_items: components["schemas"]["MatchItemResponse"][];
            /** Right Items */
            right_items: components["schemas"]["MatchItemResponse"][];
            /** Correct Pairs */
            correct_pairs: components["schemas"]["CorrectPairInput"][];
        };
        /** MatchingLearnerConfig */
        MatchingLearnerConfig: {
            /** Left Items */
            left_items: components["schemas"]["MatchItemResponse"][];
            /** Right Items */
            right_items: components["schemas"]["MatchItemResponse"][];
        };
        /** MatchingPair */
        MatchingPair: {
            /** Left Id */
            left_id: string;
            /** Right Id */
            right_id: string;
        };
        /** MessageCreateRequest */
        MessageCreateRequest: {
            /** Content */
            content: string;
        };
        /** MessagePage */
        MessagePage: {
            /** Items */
            items: components["schemas"]["MessageResponse"][];
            /** Page */
            page: number;
            /** Page Size */
            page_size: number;
            /** Total */
            total: number;
        };
        /** MessageResponse */
        MessageResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Sequence Number */
            sequence_number: number;
            /**
             * Role
             * @enum {string}
             */
            role: "USER" | "ASSISTANT";
            /** Content */
            content: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "PENDING" | "COMPLETED" | "FAILED";
            /** Reply To Message Id */
            reply_to_message_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Citations */
            citations: components["schemas"]["CitationResponse"][];
        };
        /** MultipleChoiceAnswer */
        MultipleChoiceAnswer: {
            /**
             * Option Id
             * Format: uuid
             */
            option_id: string;
        };
        /** MultipleChoiceAttemptAnswerResult */
        MultipleChoiceAttemptAnswerResult: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Prompt */
            prompt: string;
            /**
             * Grading Status
             * @enum {string}
             */
            grading_status: "PENDING" | "GRADED" | "UNCERTAIN" | "FAILED";
            /** Score */
            score: number | null;
            /** Is Correct */
            is_correct: boolean | null;
            /** Feedback */
            feedback: string | null;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "multiple_choice";
            answer: components["schemas"]["MultipleChoiceAnswer"] | null;
            config?: components["schemas"]["AnswerKeyFreeConfig"] | null;
        };
        /** PDFPageLocator */
        PDFPageLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "PDF_PAGE";
            /** Page Number */
            page_number: number;
        };
        /** PasswordResetConfirmRequest */
        PasswordResetConfirmRequest: {
            /** Token */
            token: string;
            /** New Password */
            new_password: string;
        };
        /** PasswordResetRequest */
        PasswordResetRequest: {
            /** Email */
            email: string;
        };
        /** PeriodicTestContinueLearning */
        PeriodicTestContinueLearning: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "PERIODIC_TEST";
            /** Section Id */
            section_id?: null;
            /** Code */
            code?: null;
            /** Lesson Id */
            lesson_id?: null;
            /**
             * Assessment Id
             * Format: uuid
             */
            assessment_id: string;
        };
        /** PeriodicTestGenerationRequest */
        PeriodicTestGenerationRequest: {
            /** Title */
            title?: string | null;
            /** Description */
            description?: string | null;
            /**
             * Pass Threshold
             * @default 90
             */
            pass_threshold: number;
            /** Question Count */
            question_count: number;
            /** Allowed Types */
            allowed_types: ("multiple_choice" | "fill_blank" | "matching" | "reorder_sentence" | "translate_vi_zh" | "translate_zh_vi" | "sentence_writing")[];
            /**
             * Difficulty
             * @enum {string}
             */
            difficulty: "EASY" | "MEDIUM" | "HARD";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "PERIODIC_TEST";
            /** Lesson Ids */
            lesson_ids: string[];
            /** Vocabulary Ids */
            vocabulary_ids?: string[];
            /** Grammar Ids */
            grammar_ids?: string[];
        };
        /** ProgressOverviewResponse */
        ProgressOverviewResponse: {
            /** Current Hsk */
            current_hsk: number | null;
            /** Progress Percentage */
            progress_percentage: number;
            /** Pronunciation Complete */
            pronunciation_complete: boolean;
            /** Hsk Levels */
            hsk_levels: components["schemas"]["HSKLevelResponse"][];
        };
        /** PronunciationContinueLearning */
        PronunciationContinueLearning: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "PRONUNCIATION";
            /**
             * Section Id
             * Format: uuid
             */
            section_id: string;
            /** Code */
            code: string;
            /** Lesson Id */
            lesson_id?: null;
            /** Assessment Id */
            assessment_id?: null;
        };
        /** PronunciationSectionResponse */
        PronunciationSectionResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Code */
            code: string;
            /** Title */
            title: string | null;
            /** Description */
            description: string | null;
            /** Order Index */
            order_index: number;
            /** Completed At */
            completed_at: string | null;
        };
        /** QuestionAdminResponse */
        QuestionAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Assessment Id
             * Format: uuid
             */
            assessment_id: string;
            /**
             * Type
             * @enum {string}
             */
            type: "multiple_choice" | "fill_blank" | "matching" | "reorder_sentence" | "translate_vi_zh" | "translate_zh_vi" | "sentence_writing";
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Reference Answer */
            reference_answer: string | null;
            /** Rubric */
            rubric: string | null;
            /** Config */
            config: components["schemas"]["MatchingConfigInput"] | components["schemas"]["ReorderConfigInput"] | components["schemas"]["FillBlankConfigInput"] | components["schemas"]["AnswerKeyFreeConfig"] | null;
            /** Points */
            points: number;
            /** Options */
            options: components["schemas"]["QuestionOptionAdminResponse"][];
        };
        /** QuestionCreateRequest */
        QuestionCreateRequest: {
            /**
             * Type
             * @enum {string}
             */
            type: "multiple_choice" | "fill_blank" | "matching" | "reorder_sentence" | "translate_vi_zh" | "translate_zh_vi" | "sentence_writing";
            /** Prompt */
            prompt: string;
            /** Order Index */
            order_index: number;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /** Config */
            config?: components["schemas"]["MatchingConfigInput"] | components["schemas"]["ReorderConfigInput"] | components["schemas"]["FillBlankConfigInput"] | components["schemas"]["AnswerKeyFreeConfig"] | null;
            /**
             * Points
             * @default 1
             */
            points: number;
            /** Options */
            options?: components["schemas"]["QuestionOptionInput"][] | null;
        };
        /** QuestionOptionAdminResponse */
        QuestionOptionAdminResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Option Text */
            option_text: string;
            /** Order Index */
            order_index: number;
            /** Is Correct */
            is_correct: boolean;
        };
        /** QuestionOptionInput */
        QuestionOptionInput: {
            /** Option Text */
            option_text: string;
            /** Is Correct */
            is_correct: boolean;
        };
        /** QuestionPatchRequest */
        QuestionPatchRequest: {
            /** Prompt */
            prompt?: string;
            /** Order Index */
            order_index?: number;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /** Config */
            config?: components["schemas"]["MatchingConfigInput"] | components["schemas"]["ReorderConfigInput"] | components["schemas"]["FillBlankConfigInput"] | components["schemas"]["AnswerKeyFreeConfig"] | null;
            /** Points */
            points?: number;
            /** Options */
            options?: components["schemas"]["QuestionOptionInput"][] | null;
        };
        /** RegisterRequest */
        RegisterRequest: {
            /** Email */
            email: string;
            /** Password */
            password: string;
            /** Full Name */
            full_name: string;
        };
        /** ReorderAnswer */
        ReorderAnswer: {
            /** Item Ids */
            item_ids: string[];
        };
        /** ReorderAttemptAnswerResult */
        ReorderAttemptAnswerResult: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Prompt */
            prompt: string;
            /**
             * Grading Status
             * @enum {string}
             */
            grading_status: "PENDING" | "GRADED" | "UNCERTAIN" | "FAILED";
            /** Score */
            score: number | null;
            /** Is Correct */
            is_correct: boolean | null;
            /** Feedback */
            feedback: string | null;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "reorder_sentence";
            answer: components["schemas"]["ReorderAnswer"] | null;
            config?: components["schemas"]["ResultReorderConfig"] | null;
        };
        /** ReorderConfigInput */
        ReorderConfigInput: {
            /** Items */
            items: components["schemas"]["ReorderItemResponse"][];
            /** Correct Order */
            correct_order: string[];
        };
        /** ReorderItemResponse */
        ReorderItemResponse: {
            /** Id */
            id: string;
            /** Text */
            text: string;
        };
        /** ReorderLearnerConfig */
        ReorderLearnerConfig: {
            /** Items */
            items: components["schemas"]["ReorderItemResponse"][];
        };
        /** ResultFillBlankConfig */
        ResultFillBlankConfig: {
            /** Accepted Answers */
            accepted_answers?: string[] | null;
        };
        /** ResultMatchingConfig */
        ResultMatchingConfig: {
            /** Left Items */
            left_items: components["schemas"]["MatchItemResponse"][];
            /** Right Items */
            right_items: components["schemas"]["MatchItemResponse"][];
            /** Correct Pairs */
            correct_pairs: components["schemas"]["MatchingPair"][];
        };
        /** ResultReorderConfig */
        ResultReorderConfig: {
            /** Items */
            items: components["schemas"]["ReorderItemResponse"][];
            /** Correct Order */
            correct_order: string[];
        };
        /** SendMessageResponse */
        SendMessageResponse: {
            user_message: components["schemas"]["MessageResponse"];
            assistant_message: components["schemas"]["MessageResponse"];
        };
        /** SubmissionAnswer */
        SubmissionAnswer: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Answer */
            answer: components["schemas"]["MultipleChoiceAnswer"] | components["schemas"]["FillBlankAnswer"] | components["schemas"]["MatchingAnswer"] | components["schemas"]["ReorderAnswer"] | components["schemas"]["TextAnswer"];
        };
        /** SubmitAttemptRequest */
        SubmitAttemptRequest: {
            /** Answers */
            answers: components["schemas"]["SubmissionAnswer"][];
        };
        /** TableRow */
        TableRow: {
            /** Row Index */
            row_index: number;
            /** Text */
            text: string;
        };
        /** TableStructuredData */
        TableStructuredData: {
            /** Table Index */
            table_index: number;
            /** Rows */
            rows: components["schemas"]["TableRow"][];
        };
        /** TextAnswer */
        TextAnswer: {
            /** Text */
            text: string;
        };
        /** TextAttemptAnswerResult */
        TextAttemptAnswerResult: {
            /**
             * Question Id
             * Format: uuid
             */
            question_id: string;
            /** Prompt */
            prompt: string;
            /**
             * Grading Status
             * @enum {string}
             */
            grading_status: "PENDING" | "GRADED" | "UNCERTAIN" | "FAILED";
            /** Score */
            score: number | null;
            /** Is Correct */
            is_correct: boolean | null;
            /** Feedback */
            feedback: string | null;
            /** Reference Answer */
            reference_answer?: string | null;
            /** Rubric */
            rubric?: string | null;
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            type: "sentence_writing" | "translate_vi_zh" | "translate_zh_vi";
            answer: components["schemas"]["TextAnswer"] | null;
            config?: components["schemas"]["AnswerKeyFreeConfig"] | null;
        };
        /** TextBlockLocator */
        TextBlockLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "TEXT_BLOCK";
            /** Block Index */
            block_index: number;
        };
        /** TheoryContentProgressResponse */
        TheoryContentProgressResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Viewed */
            viewed: boolean;
        };
        /** TransformedDocument */
        TransformedDocument: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "transformed_document/v1";
            /**
             * Source Type
             * @enum {string}
             */
            source_type: "DOCUMENT" | "LESSON";
            /**
             * Source Id
             * Format: uuid
             */
            source_id: string;
            /** Title */
            title: string;
            /** Source Language */
            source_language: ("vi" | "zh" | "en") | null;
            /** Source Category */
            source_category: ("CURRICULUM_MATERIAL" | "INTERNAL_AUTHORED") | null;
            /**
             * Transformation Strategy
             * @constant
             */
            transformation_strategy: "canonical_document";
            /**
             * Transformation Version
             * @constant
             */
            transformation_version: "v1";
            /** Provenance */
            provenance: components["schemas"]["DocumentProvenance"] | components["schemas"]["LessonProvenance"];
            /** Blocks */
            blocks: components["schemas"]["CanonicalBlock"][];
        };
        /** UnitProgress */
        UnitProgress: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Order Index */
            order_index: number;
            /**
             * Unit Type
             * @enum {string}
             */
            unit_type: "LESSON" | "PERIODIC_TEST";
            /**
             * State
             * @enum {string}
             */
            state: "LOCKED" | "AVAILABLE" | "COMPLETED";
            lesson?: components["schemas"]["CurriculumLessonSummary"] | null;
            assessment?: components["schemas"]["CurriculumAssessmentSummary"] | null;
        };
        /** UserProfileResponse */
        UserProfileResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Email */
            email: string;
            /** Full Name */
            full_name: string;
            /** Role */
            role: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /** ViewProgressResponse */
        ViewProgressResponse: {
            /**
             * Viewed At
             * Format: date-time
             */
            viewed_at: string;
            /** Theory Completed At */
            theory_completed_at: string | null;
        };
        /** VocabularyAttachRequest */
        VocabularyAttachRequest: {
            /**
             * Vocabulary Id
             * Format: uuid
             */
            vocabulary_id?: string;
            /** Hanzi */
            hanzi?: string;
            /** Pinyin */
            pinyin?: string;
            /** Vietnamese Meaning */
            vietnamese_meaning?: string;
            /** Part Of Speech */
            part_of_speech?: string | null;
            /** Order Index */
            order_index: number;
            /** Note */
            note?: string | null;
            /** Example */
            example?: string | null;
        };
        /** VocabularyItemResponse */
        VocabularyItemResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Hanzi */
            hanzi: string;
            /** Pinyin */
            pinyin: string;
            /** Vietnamese Meaning */
            vietnamese_meaning: string;
            /** Part Of Speech */
            part_of_speech: string | null;
        };
        /** VocabularyLessonItem */
        VocabularyLessonItem: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Order Index */
            order_index: number;
            /** Note */
            note: string | null;
            /** Example */
            example: string | null;
            item: components["schemas"]["VocabularyItemResponse"];
        };
        /** VocabularyPatchRequest */
        VocabularyPatchRequest: {
            /** Order Index */
            order_index?: number;
            /** Note */
            note?: string | null;
            /** Example */
            example?: string | null;
            /** Hanzi */
            hanzi?: string;
            /** Pinyin */
            pinyin?: string;
            /** Vietnamese Meaning */
            vietnamese_meaning?: string;
            /** Part Of Speech */
            part_of_speech?: string | null;
        };
        /** VocabularyStructuredData */
        VocabularyStructuredData: {
            /**
             * Lesson Id
             * Format: uuid
             */
            lesson_id: string;
            /**
             * Vocabulary Id
             * Format: uuid
             */
            vocabulary_id: string;
            /** Hanzi */
            hanzi?: string | null;
            /** Pinyin */
            pinyin?: string | null;
            /** Vietnamese Meaning */
            vietnamese_meaning?: string | null;
            /** Part Of Speech */
            part_of_speech?: string | null;
            /** Example */
            example?: string | null;
            /** Note */
            note?: string | null;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    register_api_v1_auth_register_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login_api_v1_auth_login_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    me_api_v1_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserProfileResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    refresh_api_v1_auth_refresh_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                refresh_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_api_v1_auth_logout_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                refresh_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout_all_api_v1_auth_logout_all_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    change_password_api_v1_auth_change_password_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ChangePasswordRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    password_reset_request_api_v1_auth_password_reset_request_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    password_reset_confirm_api_v1_auth_password_reset_confirm_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetConfirmRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_conversation_api_v1_conversations_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_conversations_api_v1_me_conversations_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                lesson_id?: string | null;
                scope?: "LESSON" | null;
            };
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_conversation_api_v1_conversations__conversation_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_conversation_api_v1_conversations__conversation_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    rename_conversation_api_v1_conversations__conversation_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ConversationPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    message_history_api_v1_conversations__conversation_id__messages_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessagePage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    send_message_api_v1_conversations__conversation_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MessageCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SendMessageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_message_api_v1_messages__assistant_message_id__retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assistant_message_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    dashboard_api_v1_me_dashboard_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DashboardResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pronunciation_api_v1_pronunciation_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PronunciationSectionResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    pronunciation_complete_api_v1_pronunciation__section_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                section_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: unknown;
                    };
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    vocabulary_view_api_v1_lessons__lesson_id__theory_vocabulary__lesson_vocabulary_id__view_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                lesson_vocabulary_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ViewProgressResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    grammar_view_api_v1_lessons__lesson_id__theory_grammar__lesson_grammar_id__view_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                lesson_grammar_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ViewProgressResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    progress_api_v1_me_progress_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProgressOverviewResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    hsk_progress_api_v1_me_progress_hsk__hsk_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                hsk_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HSKProgressResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lesson_progress_api_v1_me_progress_lessons__lesson_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonProgressResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    hsk_levels_api_v1_hsk_levels_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HSKLevelResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    curriculum_api_v1_hsk_levels__hsk_id__curriculum_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                hsk_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CurriculumResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lesson_api_v1_lessons__lesson_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assessment_api_v1_assessments__assessment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_api_v1_assessments__assessment_id__attempts_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttemptResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_api_v1_assessment_attempts__attempt_id__submit_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attempt_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SubmitAttemptRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttemptSubmissionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    history_api_v1_me_assessment_attempts_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
                assessment_id?: string | null;
                lesson_id?: string | null;
                assessment_type?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttemptHistoryPage"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    detail_api_v1_me_assessment_attempts__attempt_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attempt_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttemptDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_documents_api_v1_admin_documents_get: {
        parameters: {
            query?: {
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentAdminPageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_document_api_v1_admin_documents_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_document_api_v1_admin_documents_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentRawIngestionResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_document_detail_api_v1_admin_documents__document_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DocumentAdminDetailResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    process_document_api_v1_admin_documents__document_id__process_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    preview_document_api_v1_admin_documents__document_id__preview_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TransformedDocument"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    approve_document_api_v1_admin_documents__document_id__approve_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reject_document_api_v1_admin_documents__document_id__reject_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_document_knowledge_api_v1_admin_documents__document_id__knowledge_retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                document_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    hsk_levels_api_v1_admin_hsk_levels_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HSKAdminResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_hsk_api_v1_admin_hsk_levels__hsk_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                hsk_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["HSKPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HSKAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_curriculum_api_v1_admin_hsk_levels__hsk_id__curriculum_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                hsk_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminCurriculumUnitResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    put_curriculum_api_v1_admin_hsk_levels__hsk_id__curriculum_put: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                hsk_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CurriculumPutRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminCurriculumUnitResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    lessons_api_v1_admin_lessons_get: {
        parameters: {
            query?: {
                status?: string | null;
                hsk_level_id?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminPageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_lesson_api_v1_admin_lessons_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LessonCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_lesson_api_v1_admin_lessons__lesson_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_lesson_api_v1_admin_lessons__lesson_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LessonPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_lesson_api_v1_admin_lessons__lesson_id__publish_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_lesson_knowledge_api_v1_admin_lessons__lesson_id__knowledge_retry_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_lesson_api_v1_admin_lessons__lesson_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_items_api_v1_admin_lessons__lesson_id__vocabulary_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    attach_api_v1_admin_lessons__lesson_id__vocabulary_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VocabularyAttachRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    detach_api_v1_admin_lessons__lesson_id__vocabulary__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                item_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_api_v1_admin_lessons__lesson_id__vocabulary__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                item_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["VocabularyPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_items_api_v1_admin_lessons__lesson_id__grammar_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    attach_api_v1_admin_lessons__lesson_id__grammar_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GrammarAttachRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    detach_api_v1_admin_lessons__lesson_id__grammar__item_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                item_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_api_v1_admin_lessons__lesson_id__grammar__item_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                lesson_id: string;
                item_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GrammarPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LessonContentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    assessments_api_v1_admin_assessments_get: {
        parameters: {
            query?: {
                status?: string | null;
                assessment_type?: string | null;
                page?: number;
                page_size?: number;
            };
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminPageResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_assessment_api_v1_admin_assessments_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssessmentCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    generate_assessment_draft_api_v1_admin_assessments_generate_draft_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LessonExerciseGenerationRequest"] | components["schemas"]["PeriodicTestGenerationRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentGenerationDraftResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_assessment_api_v1_admin_assessments__assessment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_assessment_api_v1_admin_assessments__assessment_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssessmentPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    questions_api_v1_admin_assessments__assessment_id__questions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionAdminResponse"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_question_api_v1_admin_assessments__assessment_id__questions_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_question_api_v1_admin_assessments__assessment_id__questions__question_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
                question_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_question_api_v1_admin_assessments__assessment_id__questions__question_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
                question_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["QuestionPatchRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["QuestionAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    submit_review_api_v1_admin_assessments__assessment_id__submit_review_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    publish_assessment_api_v1_admin_assessments__assessment_id__publish_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_assessment_api_v1_admin_assessments__assessment_id__archive_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                assessment_id: string;
            };
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssessmentAdminResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stats_api_v1_admin_stats_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: {
                access_token?: string | null;
            };
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AdminStatsResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    health_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    readiness_ready_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}
