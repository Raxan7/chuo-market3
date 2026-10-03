def user_owns_course(user, course):
    """
    Return True only when the authenticated user owns/instructs
    this course.

    ChuoSmart installations have historically represented course
    ownership through instructor/profile relations, so this helper
    intentionally supports both a direct User relation and a profile
    relation with .user_id.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    user_id = getattr(user, "pk", None)

    if user_id is None:
        return False

    for attribute in (
        "instructor",
        "creator",
        "created_by",
        "owner",
    ):
        relation = getattr(
            course,
            attribute,
            None,
        )

        if relation is None:
            continue

        # LMSProfile / instructor-profile relationship.
        if getattr(
            relation,
            "user_id",
            None,
        ) == user_id:
            return True

        related_user = getattr(
            relation,
            "user",
            None,
        )

        if (
            related_user is not None
            and getattr(
                related_user,
                "pk",
                None,
            ) == user_id
        ):
            return True

        # Direct django.contrib.auth User relationship.
        if (
            hasattr(
                relation,
                "is_authenticated",
            )
            and getattr(
                relation,
                "pk",
                None,
            ) == user_id
        ):
            return True

    return False
