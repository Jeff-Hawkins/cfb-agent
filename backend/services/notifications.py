"""Email notification service for CFB Agent pick alerts.

Sends a plain-text email via SendGrid when new picks are ready for review.
SENDGRID_API_KEY and NOTIFY_EMAIL must be set as environment variables.
Failures are logged but do not raise, so the calling endpoint is never crashed
by an email delivery issue.
"""

import os
import logging

logger = logging.getLogger(__name__)


def send_picks_ready_email(picks: list, week: int, season: int) -> None:
    """Send a 'picks ready for review' email via SendGrid.

    Args:
        picks: List of pick dicts as produced by the /picks/flag endpoint.
        week: The CFB week number.
        season: The season year.

    The function silently returns (logging an error) if SendGrid is
    unavailable or improperly configured.
    """
    api_key = os.getenv("SENDGRID_API_KEY", "")
    notify_email = os.getenv("NOTIFY_EMAIL", "")

    if not api_key or not notify_email:
        logger.warning(
            "SENDGRID_API_KEY or NOTIFY_EMAIL not set — skipping email notification"
        )
        return

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        lines = []
        for pick in picks:
            opponent = pick["away_team"] if pick["pick_team"] == pick["home_team"] else pick["home_team"]
            win_pct = pick["win_probability"] * 100
            lines.append(
                f"  {pick['pick_team']} vs {opponent} | "
                f"{pick['confidence_label']} | "
                f"Win Prob: {win_pct:.1f}% | "
                f"Model Edge: {pick['model_spread_diff']:.1f} pts"
            )

        body = (
            f"CFB Agent has flagged {len(picks)} pick(s) for Week {week}, {season}:\n\n"
            + "\n".join(lines)
            + "\n\nLogin to review: https://cfb-agent.vercel.app/admin"
        )

        message = Mail(
            from_email=notify_email,
            to_emails=notify_email,
            subject=f"CFB Agent — Week {week} picks ready for review",
            plain_text_content=body,
        )

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        logger.info(
            "Picks-ready email sent (status %s) for Week %d %d",
            response.status_code,
            week,
            season,
        )

    except Exception as exc:
        logger.error("Failed to send picks-ready email: %s", exc)
