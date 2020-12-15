from dataclasses import asdict, dataclass, field
from typing import Any, Collection, Dict, List, Optional, Set

from fixit.common.report import BaseLintRuleReport

from algorithms_keeper.constants import Label

# Mapping of rule to the appropriate label.
RULE_TO_LABEL: Dict[str, str] = {
    "RequireDescriptiveNameRule": Label.DESCRIPTIVE_NAME,
    "RequireDoctestRule": Label.REQUIRE_TEST,
    "RequireTypeHintRule": Label.TYPE_HINT,
}


@dataclass(frozen=False)
class ReviewComment:
    # Text of the review comment. This is different from the body of the review itself.
    body: str

    # The relative path to the file that necessitates a review comment.
    path: str

    # The line of the blob in the pull request diff that the comment applies to.
    line: int

    # In a split diff view, the side of the diff that the pull request's changes appear
    # on. As we can only comment on a line present in the pull request diff, we default
    # to the RIGHT side.
    #
    # From GitHub:
    # Can be LEFT or RIGHT. Use LEFT for deletions that appear in red. Use RIGHT for
    # additions that appear in green or unchanged lines that appear in white and are
    # shown for context.
    side: str = field(init=False, default="RIGHT")


@dataclass(frozen=False)
class PullRequestReviewRecord:
    """A Record object to store the necessary information regarding the current pull
    request. This should only be initialized once per pull request and use its public
    interface to add and get the appropriate data.
    """

    # Initialize the label attributes. These should be filled with the appropriate
    # labels **only** after all the files have been linted.
    labels_to_add: List[str] = field(default_factory=list)
    labels_to_remove: List[str] = field(default_factory=list)

    # Store all the ``ReviewComment`` instances.
    _comments: List[ReviewComment] = field(default_factory=list)

    # A set of rules which were violated during the runtime of the parser for the
    # current pull request. This is being represented as ``set`` internally to avoid
    # duplication.
    _violated_rules: Set[str] = field(default_factory=set)

    def add_comments(
        self, reports: Collection[BaseLintRuleReport], filepath: str
    ) -> None:
        """Add a comments from the reports.

        If the line on which the comment is to be posted already exists, then the
        *body* is simply added to the respective comment's body provided it is in the
        same file. This is done to avoid adding multiple comments on the same line.
        """
        for report in reports:
            line: int = report.line
            message: str = report.message
            self._violated_rules.add(report.code)
            if self._lineno_exist(line, filepath, message):
                continue
            self._comments.append(ReviewComment(message, filepath, line))

    def add_error(self, message: str, filepath: str, lineno: Optional[int]) -> None:
        """Add any exceptions faced while parsing the source code in the parser_old.

        The parameter *message* is the traceback text with limit=1, no need for the
        full traceback.
        """
        if lineno is None:  # pragma: no cover
            lineno = 1
        body = (
            f"An error occured while parsing the file: `{filepath}`\n"
            f"```python\n{message}\n```"
        )
        self._comments.append(ReviewComment(body, filepath, lineno))

    def fill_labels(self, current_labels: List[str]) -> None:
        """Fill the ``add_labels`` and ``remove_labels`` with the appropriate data.

        This method is **only** to be called once after all the files have been parsed.

        *current_labels* is a list of labels present on the pull request.
        """
        for rule, label in RULE_TO_LABEL.items():
            if rule in self._violated_rules:
                if label not in current_labels and label not in self.labels_to_add:
                    self.labels_to_add.append(label)
            elif label in current_labels and label not in self.labels_to_remove:
                self.labels_to_remove.append(label)

    def collect_comments(self) -> List[Dict[str, Any]]:
        """Return all the review comments in the record instance.

        This is how GitHub wants the *comments* value while creating the review.
        """
        return [asdict(comment) for comment in self._comments]

    def _lineno_exist(self, lineno: int, filepath: str, body: str) -> bool:
        """Determine whether any review comment is registered for the given *lineno*
        for the given *filepath*.

        If ``True``, add the provided *body* to the respective comment body. This helps
        in avoiding multiple review comments on the same line.
        """
        for comment in self._comments:
            if comment.line == lineno and comment.path == filepath:
                comment.body += f"\n\n{body}"
                return True
        return False