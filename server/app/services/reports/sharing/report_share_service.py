"""리포트 공유 서비스."""

from __future__ import annotations

from server.app.domain.models.report import Report
from server.app.domain.models.report_share import (
    ReceivedReportShareView,
    ReportShare,
    ReportShareView,
)
from server.app.domain.models.user import UserAccount
from server.app.repositories.contracts.report_share_repository import ReportShareRepository


class ReportShareServiceError(Exception):
    """리포트 공유 서비스 공통 예외."""


class ShareRecipientNotFoundError(ReportShareServiceError):
    """공유 대상을 찾지 못한 경우."""


class DuplicateReportShareError(ReportShareServiceError):
    """이미 같은 대상에게 공유한 경우."""


class InvalidReportShareTargetError(ReportShareServiceError):
    """공유 대상을 잘못 지정한 경우."""


class ReportShareService:
    """리포트 공유를 생성하고 조회한다."""

    def __init__(
        self,
        *,
        auth_repository,
        report_share_repository: ReportShareRepository,
    ) -> None:
        self._auth_repository = auth_repository
        self._report_share_repository = report_share_repository

    def create_share(
        self,
        *,
        report: Report,
        shared_by_user: UserAccount,
        shared_with_login_id: str,
        note: str | None = None,
    ) -> ReportShareView:
        """리포트를 다른 사용자에게 공유한다."""

        recipient = self._auth_repository.get_user_by_login_id(
            shared_with_login_id.strip().lower()
        )
        if recipient is None or recipient.status != "active":
            raise ShareRecipientNotFoundError("공유할 사용자를 찾지 못했습니다.")
        if recipient.id == shared_by_user.id:
            raise InvalidReportShareTargetError("본인에게 리포트를 공유할 수는 없습니다.")

        existing_share = self._report_share_repository.get_by_report_and_recipient(
            report_id=report.id,
            shared_with_user_id=recipient.id,
        )
        if existing_share is not None:
            raise DuplicateReportShareError("이미 같은 사용자에게 공유된 리포트입니다.")

        share = ReportShare.create(
            report_id=report.id,
            shared_by_user_id=shared_by_user.id,
            shared_with_user_id=recipient.id,
            permission="view",
            note=(note.strip() or None) if note is not None else None,
        )
        return self._report_share_repository.save(share)

    def get_share_for_recipient(
        self,
        *,
        report_id: str,
        shared_with_user_id: str,
    ) -> ReportShare | None:
        """특정 수신자 기준 공유 레코드를 조회한다."""

        return self._report_share_repository.get_by_report_and_recipient(
            report_id=report_id,
            shared_with_user_id=shared_with_user_id,
        )

    def list_shares(self, report_id: str) -> list[ReportShareView]:
        """리포트 공유 목록을 조회한다."""

        return self._report_share_repository.list_by_report(report_id)

    def list_received_shares(
        self,
        *,
        shared_with_user_id: str,
        limit: int = 50,
    ) -> list[ReceivedReportShareView]:
        """사용자가 공유받은 리포트 목록을 조회한다."""

        return self._report_share_repository.list_received_by_user(
            shared_with_user_id=shared_with_user_id,
            limit=limit,
        )
