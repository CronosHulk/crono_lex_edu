from __future__ import annotations

from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_ARCHIVED as USER_WORD_ASSIGNMENT_ARCHIVED,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_AVAILABLE as USER_WORD_ASSIGNMENT_AVAILABLE,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_HIDDEN as USER_WORD_ASSIGNMENT_HIDDEN,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_ASSIGNMENT_WAITING as USER_WORD_ASSIGNMENT_WAITING,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_SOURCE_CORE as USER_WORD_SOURCE_CORE,
)
from app.domain.user_dictionary.constants import (
    USER_WORD_SOURCE_USER as USER_WORD_SOURCE_USER,
)

USER_WORD_PRIORITY_NONE = "none"
USER_WORD_PRIORITY_PENDING = "pending"
USER_WORD_PRIORITY_INTRODUCED = "introduced"
USER_WORD_PRIORITY_CONSUMED = "consumed"
USER_WORD_LEARNING = "learning"
USER_WORD_NEEDS_WORK = "needs_work"
USER_WORD_LEARNED = "learned"
