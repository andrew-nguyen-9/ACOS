from __future__ import annotations

# Section density caps per Resume Engine Spec v1.0
_CURRENT_ROLE_CAP = 6
_PREVIOUS_ROLE_CAP = 4


class ContentSelector:
    """Choose which scored bullets appear on the resume vs. flow to the cover letter.

    Selection order: highest-score first, constrained by per-experience density caps.
    All bullets that don't make the cut go to ``excluded_bullets`` for the CL pipeline.
    """

    def select(
        self,
        bullets: list[dict],
        max_bullets: int,
    ) -> tuple[list[dict], list[dict]]:
        """Partition bullets into (selected, excluded).

        Args:
            bullets: Scored bullet dicts (must have ``score`` and ``experience_id`` keys).
            max_bullets: Hard ceiling on total selected bullets.

        Returns:
            Tuple of (selected_bullets, excluded_bullets). Both preserve original dict fields.
        """
        if not bullets:
            return [], []

        sorted_bullets = sorted(bullets, key=lambda b: b.get("score", 0.0), reverse=True)

        selected: list[dict] = []
        excluded: list[dict] = []
        per_exp_count: dict[str, int] = {}

        for bullet in sorted_bullets:
            if len(selected) >= max_bullets:
                excluded.append(bullet)
                continue

            exp_id = bullet.get("experience_id", "unknown")
            cap = _CURRENT_ROLE_CAP if bullet.get("is_current", False) else _PREVIOUS_ROLE_CAP
            count = per_exp_count.get(exp_id, 0)

            if count >= cap:
                excluded.append(bullet)
            else:
                selected.append(bullet)
                per_exp_count[exp_id] = count + 1

        return selected, excluded
