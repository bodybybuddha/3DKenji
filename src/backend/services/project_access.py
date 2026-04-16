"""Project access policy helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.project import Project
from backend.models.project_collaborator import ProjectCollaborator
from backend.models.project_invitation import ProjectInvitation
from backend.models.user import User

READ_ROLES = {"viewer", "editor"}
EDIT_ROLES = {"editor"}
MANAGE_ROLES = set()


class ProjectAccessService:
    """Permission checks and invitation/collaboration workflows."""

    def __init__(self, session: Session):
        self.session = session

    def is_owner(self, project: Project, user_id: Optional[str]) -> bool:
        return bool(user_id and project.owner_id == user_id)

    def collaborator_role(self, project_id: str, user_id: Optional[str]) -> Optional[str]:
        if not user_id:
            return None
        collaborator = self.session.execute(
            select(ProjectCollaborator).where(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == user_id,
            )
        ).scalar_one_or_none()
        return collaborator.role if collaborator else None

    def can_view(self, project: Project, user_id: Optional[str]) -> bool:
        if self.is_owner(project, user_id):
            return True
        if project.visibility == "public":
            return True
        role = self.collaborator_role(project.id, user_id)
        return bool(role in READ_ROLES)

    def can_edit(self, project: Project, user_id: Optional[str]) -> bool:
        if self.is_owner(project, user_id):
            return True
        role = self.collaborator_role(project.id, user_id)
        return bool(role in EDIT_ROLES)

    def can_manage_access(self, project: Project, user_id: Optional[str]) -> bool:
        if self.is_owner(project, user_id):
            return True
        role = self.collaborator_role(project.id, user_id)
        return bool(role in MANAGE_ROLES)

    def upsert_collaborator(
        self,
        project: Project,
        target_user_id: str,
        role: str,
        granted_by_id: str,
    ) -> ProjectCollaborator:
        existing = self.session.execute(
            select(ProjectCollaborator).where(
                ProjectCollaborator.project_id == project.id,
                ProjectCollaborator.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if existing:
            existing.role = role
            existing.granted_by_id = granted_by_id
            self.session.commit()
            self.session.refresh(existing)
            return existing

        collaborator = ProjectCollaborator(
            project_id=project.id,
            user_id=target_user_id,
            role=role,
            granted_by_id=granted_by_id,
        )
        self.session.add(collaborator)
        self.session.commit()
        self.session.refresh(collaborator)
        return collaborator

    def remove_collaborator(self, project_id: str, target_user_id: str) -> bool:
        existing = self.session.execute(
            select(ProjectCollaborator).where(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == target_user_id,
            )
        ).scalar_one_or_none()
        if not existing:
            return False
        self.session.delete(existing)
        self.session.commit()
        return True

    def list_collaborators(self, project_id: str) -> list[ProjectCollaborator]:
        return self.session.execute(
            select(ProjectCollaborator)
            .where(ProjectCollaborator.project_id == project_id)
            .order_by(ProjectCollaborator.created_at.asc())
        ).scalars().all()

    def create_invitation(
        self,
        project: Project,
        invited_email: str,
        role: str,
        token_hash: str,
        expires_at,
        invited_by_id: str,
    ) -> ProjectInvitation:
        invitation = ProjectInvitation(
            project_id=project.id,
            invited_email=invited_email.lower(),
            role=role,
            token_hash=token_hash,
            invited_by_id=invited_by_id,
            expires_at=expires_at,
        )
        self.session.add(invitation)
        self.session.commit()
        self.session.refresh(invitation)
        return invitation

    def list_invitations(
        self,
        project_id: str,
        include_inactive: bool = False,
    ) -> list[ProjectInvitation]:
        query = select(ProjectInvitation).where(ProjectInvitation.project_id == project_id)
        if not include_inactive:
            query = query.where(ProjectInvitation.accepted_at.is_(None))
            query = query.where(ProjectInvitation.revoked_at.is_(None))

        return self.session.execute(
            query.order_by(ProjectInvitation.created_at.desc())
        ).scalars().all()

    def list_pending_invitations_for_user(self, user_id: str) -> list[ProjectInvitation]:
        user = self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user:
            return []

        return self.session.execute(
            select(ProjectInvitation)
            .where(ProjectInvitation.invited_email == user.email.lower())
            .where(ProjectInvitation.accepted_at.is_(None))
            .where(ProjectInvitation.revoked_at.is_(None))
            .order_by(ProjectInvitation.created_at.desc())
        ).scalars().all()

    def update_invitation_role(
        self,
        invitation_id: str,
        role: str,
    ) -> Optional[ProjectInvitation]:
        invitation = self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
        ).scalar_one_or_none()
        if not invitation:
            return None
        if invitation.accepted_at or invitation.revoked_at:
            return None

        invitation.role = role
        self.session.commit()
        self.session.refresh(invitation)
        return invitation

    def revoke_invitation(self, invitation_id: str) -> bool:
        invitation = self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
        ).scalar_one_or_none()
        if not invitation:
            return False
        if invitation.revoked_at is not None:
            return True

        invitation.revoked_at = datetime.now(timezone.utc)
        self.session.commit()
        return True

    def accept_invitation(self, token_hash: str, user_id: str) -> Optional[ProjectCollaborator]:
        invitation = self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.token_hash == token_hash)
        ).scalar_one_or_none()
        if not invitation:
            return None

        return self._accept_invitation_record(invitation=invitation, user_id=user_id)

    def accept_invitation_by_id(self, invitation_id: str, user_id: str) -> Optional[ProjectCollaborator]:
        invitation = self.session.execute(
            select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
        ).scalar_one_or_none()
        if not invitation:
            return None

        return self._accept_invitation_record(invitation=invitation, user_id=user_id)

    def _accept_invitation_record(
        self,
        invitation: ProjectInvitation,
        user_id: str,
    ) -> Optional[ProjectCollaborator]:
        """Validate and accept a pending invitation for the authenticated user."""

        now = datetime.now(timezone.utc)
        if invitation.accepted_at or invitation.revoked_at or invitation.expires_at.replace(tzinfo=timezone.utc) <= now:
            return None

        user = self.session.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if not user or user.email.lower() != invitation.invited_email.lower():
            return None

        project = self.session.execute(select(Project).where(Project.id == invitation.project_id)).scalar_one()
        collaborator = self.upsert_collaborator(
            project=project,
            target_user_id=user_id,
            role=invitation.role,
            granted_by_id=invitation.invited_by_id,
        )

        invitation.accepted_at = now
        self.session.commit()
        return collaborator