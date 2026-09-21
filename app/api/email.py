
from fastapi import APIRouter, HTTPException
from email.message import EmailMessage
from email.utils import make_msgid
from pathlib import Path
import logging
import html
import urllib.request

import aiosmtplib

from app.core.settings import settings
from app.schemas.email import EmailRequest


router = APIRouter(
    prefix="/email",
    tags=["Email"]
)


# =========================================================
# CONFIGURATION
# =========================================================

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Hero image used inside the email
BASE_DIR = Path(__file__).resolve().parent.parent
HERO_IMAGE = BASE_DIR / "assets" / "eden_hazard.jpg"


# =========================================================
# LOGGING
# =========================================================

logger = logging.getLogger("sendemail")
logger.setLevel(logging.INFO)

if not logger.handlers:

    file_handler = logging.FileHandler(
        LOG_DIR / "sendemail.log",
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)


# =========================================================
# SEND EMAIL
# =========================================================

@router.post("/send")
async def send_email(payload: EmailRequest):

    email = payload.email
    name = payload.name.strip()

    # Safely escape user-provided name before inserting into HTML
    safe_name = html.escape(name)

    # =====================================================
    # REQUEST LOG
    # =====================================================

    logger.info(
        "EMAIL_REQUEST | to=%s | name=%s",
        email,
        name
    )

    # =====================================================
    # CREATE EMAIL
    # =====================================================

    message = EmailMessage()

    sender_email = settings.EMAIL_FROM

    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "DataFuse AI – Project Milestone Update"

    # =====================================================
    # INLINE IMAGE CID
    # =====================================================

    hero_cid = make_msgid(domain="datafuseai.local")

    # Remove < > because the HTML cid reference should contain
    # only the CID value.
    hero_cid_value = hero_cid[1:-1]

    # =====================================================
    # HTML EMAIL
    # =====================================================

    html_content = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="x-apple-disable-message-reformatting"
>

<title>DataFuse AI – Project Update</title>

<style>

    body {{
        margin: 0;
        padding: 0;
        background-color: #eef2f7;
        font-family:
            Arial,
            Helvetica,
            sans-serif;
        -webkit-font-smoothing: antialiased;
    }}

    table {{
        border-collapse: collapse;
    }}

    img {{
        border: 0;
        outline: none;
        text-decoration: none;
        display: block;
    }}

    .email-wrapper {{
        width: 100%;
        background-color: #eef2f7;
    }}

    .container {{
        width: 680px;
        max-width: 680px;
    }}

    .card {{
        background-color: #ffffff;
        border-radius: 16px;
        overflow: hidden;
    }}

    .brand {{
        font-size: 25px;
        line-height: 30px;
        font-weight: 700;
        color: #ffffff;
    }}

    .brand-accent {{
        color: #5b8def;
    }}

    .top-label {{
        color: #aeb8c7;
        font-size: 11px;
        line-height: 16px;
        font-weight: 700;
        letter-spacing: 1.2px;
    }}

    .badge {{
        display: inline-block;
        background-color: #eaf1ff;
        color: #2457d6;
        border-radius: 30px;
        padding: 7px 13px;
        font-size: 10px;
        line-height: 14px;
        font-weight: 700;
        letter-spacing: 1px;
    }}

    .headline {{
        margin: 20px 0 0 0;
        font-size: 36px;
        line-height: 43px;
        font-weight: 700;
        color: #111827;
    }}

    .intro-text {{
        margin: 16px 0 0 0;
        font-size: 15px;
        line-height: 25px;
        color: #5b6472;
    }}

    .section-title {{
        margin: 0;
        font-size: 22px;
        line-height: 29px;
        font-weight: 700;
        color: #111827;
    }}

    .section-text {{
        margin: 10px 0 0 0;
        font-size: 14px;
        line-height: 23px;
        color: #697386;
    }}

    .metric-number {{
        font-size: 27px;
        line-height: 32px;
        font-weight: 700;
        color: #111827;
    }}

    .metric-label {{
        margin-top: 5px;
        font-size: 10px;
        line-height: 15px;
        font-weight: 700;
        letter-spacing: 0.8px;
        color: #8a94a6;
    }}

    .pipeline-number {{
        width: 32px;
        height: 32px;
        line-height: 32px;
        border-radius: 50%;
        background-color: #eef3ff;
        color: #315fd8;
        font-size: 13px;
        font-weight: 700;
        text-align: center;
    }}

    .pipeline-title {{
        font-size: 15px;
        line-height: 20px;
        font-weight: 700;
        color: #1f2937;
    }}

    .pipeline-description {{
        margin-top: 5px;
        font-size: 12px;
        line-height: 18px;
        color: #7a8494;
    }}

    .completed {{
        display: inline-block;
        margin-top: 9px;
        padding: 4px 8px;
        border-radius: 20px;
        background-color: #eaf8f0;
        color: #17864b;
        font-size: 9px;
        line-height: 12px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}

    .milestone {{
        background-color: #f7f9fc;
        border: 1px solid #e5eaf1;
        border-radius: 12px;
    }}

    .milestone-number {{
        font-size: 22px;
        line-height: 27px;
        font-weight: 700;
        color: #111827;
    }}

    .milestone-text {{
        font-size: 12px;
        line-height: 18px;
        color: #697386;
    }}

    .footer {{
        font-size: 11px;
        line-height: 18px;
        color: #8b95a5;
    }}

    .footer-brand {{
        font-size: 15px;
        font-weight: 700;
        color: #4b5563;
    }}

    @media only screen and (max-width: 700px) {{

        .container {{
            width: 100% !important;
            max-width: 100% !important;
        }}

        .mobile-padding {{
            padding-left: 22px !important;
            padding-right: 22px !important;
        }}

        .headline {{
            font-size: 28px !important;
            line-height: 35px !important;
        }}

        .brand {{
            font-size: 22px !important;
        }}

        .metric-number {{
            font-size: 23px !important;
        }}

    }}

</style>

</head>


<body>

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    class="email-wrapper"
>

<tr>

<td
    align="center"
    style="padding: 30px 12px;"
>

<table
    class="container"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td class="card">


<!-- ================================================= -->
<!-- HEADER -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    style="
        background-color:#111827;
        padding:25px 30px;
    "
>

<span class="brand">
    DataFuse<span class="brand-accent">AI</span>
</span>

</td>


<td
    align="right"
    style="
        background-color:#111827;
        padding:25px 30px;
    "
>

<span class="top-label">
    PROJECT UPDATE
</span>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- HERO IMAGE -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td>

<img
    src="cid:{hero_cid_value}"
    width="680"
    alt="DataFuse AI project update"
    style="
        width:100%;
        max-width:680px;
        height:auto;
        display:block;
    "
>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- INTRODUCTION -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    class="mobile-padding"
    style="
        padding:38px 42px 20px 42px;
    "
>

<span class="badge">
    PROJECT MILESTONE
</span>


<h1 class="headline">

From demolition notices
to material &amp; carbon intelligence.

</h1>


<p class="intro-text">

Hello {safe_name},

</p>


<p class="intro-text">

We are excited to share a major milestone in the
<strong style="color:#111827;">Dutch</strong>
project.

The core data pipeline has now progressed from Dutch
demolition notices through BAG and 3DBAG enrichment
to building material estimation and embodied carbon
analysis.

</p>


</td>

</tr>

</table>


<!-- ================================================= -->
<!-- KEY METRICS -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="padding:0 30px 30px 30px;"
>

<tr>

<td
    width="33.33%"
    align="center"
    style="
        padding:20px 8px;
        border-top:1px solid #e7ebf0;
        border-bottom:1px solid #e7ebf0;
    "
>

<div class="metric-number">
    1,081
</div>

<div class="metric-label">
    BUILDINGS
</div>

</td>


<td
    width="33.33%"
    align="center"
    style="
        padding:20px 8px;
        border-top:1px solid #e7ebf0;
        border-bottom:1px solid #e7ebf0;
        border-left:1px solid #e7ebf0;
        border-right:1px solid #e7ebf0;
    "
>

<div class="metric-number">
    3
</div>

<div class="metric-label">
    DATA SOURCES
</div>

</td>


<td
    width="33.33%"
    align="center"
    style="
        padding:20px 8px;
        border-top:1px solid #e7ebf0;
        border-bottom:1px solid #e7ebf0;
    "
>

<div class="metric-number">
    CO₂
</div>

<div class="metric-label">
    ANALYSIS
</div>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- DATA PIPELINE -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    class="mobile-padding"
    style="
        padding:10px 42px 30px 42px;
    "
>

<h2 class="section-title">
    Data pipeline completed
</h2>


<p class="section-text">

The project now connects multiple Dutch building-data
sources into one structured workflow.

</p>


<!-- PIPELINE 1 -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        margin-top:22px;
        border:1px solid #e6eaf0;
        border-radius:12px;
    "
>

<tr>

<td
    width="48"
    valign="top"
    style="padding:18px 0 18px 18px;"
>

<div class="pipeline-number">
    01
</div>

</td>


<td
    valign="top"
    style="padding:18px 18px 18px 12px;"
>

<div class="pipeline-title">
    KOOP — Demolition notices
</div>

<div class="pipeline-description">

Dutch official publication data is collected,
filtered and transformed into structured demolition
records containing addresses and publication details.

</div>

<span class="completed">
    COMPLETED
</span>

</td>

</tr>

</table>


<!-- PIPELINE 2 -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        margin-top:10px;
        border:1px solid #e6eaf0;
        border-radius:12px;
    "
>

<tr>

<td
    width="48"
    valign="top"
    style="padding:18px 0 18px 18px;"
>

<div class="pipeline-number">
    02
</div>

</td>


<td
    valign="top"
    style="padding:18px 18px 18px 12px;"
>

<div class="pipeline-title">
    PDOK / BAG — Building identification
</div>

<div class="pipeline-description">

Demolition locations are matched with BAG building
objects, including PAND identifiers, construction
year, building function and geometry.

</div>

<span class="completed">
    COMPLETED
</span>

</td>

</tr>

</table>


<!-- PIPELINE 3 -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="
        margin-top:10px;
        border:1px solid #e6eaf0;
        border-radius:12px;
    "
>

<tr>

<td
    width="48"
    valign="top"
    style="padding:18px 0 18px 18px;"
>

<div class="pipeline-number">
    03
</div>

</td>


<td
    valign="top"
    style="padding:18px 18px 18px 12px;"
>

<div class="pipeline-title">
    3DBAG — 3D building enrichment
</div>

<div class="pipeline-description">

Three-dimensional building information is added,
including height, volume, roof characteristics and
other geometric properties.

</div>

<span class="completed">
    COMPLETED
</span>

</td>

</tr>

</table>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- MATERIAL & CARBON -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    class="mobile-padding"
    style="
        padding:10px 42px 38px 42px;
    "
>

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    class="milestone"
>

<tr>

<td style="padding:26px 26px 24px 26px;">

<span class="badge">
    COMPLETED MILESTONE
</span>


<h2
    class="section-title"
    style="margin-top:16px;"
>

Material estimation &amp;
embodied carbon

</h2>


<p class="section-text">

The enriched building dataset now provides the
foundation for estimating demolition material
quantities and associated embodied carbon.

Building characteristics such as construction cohort,
building type, floor area, height and 3D volume are
used to support the material estimation workflow.

</p>


<!-- MATERIAL ITEMS -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="margin-top:20px;"
>

<tr>

<td
    width="50%"
    valign="top"
    style="padding-right:8px;"
>

<div class="milestone-number">
    Materials
</div>

<div class="milestone-text">

Steel, copper, aluminium, wood, concrete, brick,
glass, plastics, insulation and other material groups.

</div>

</td>


<td
    width="50%"
    valign="top"
    style="padding-left:8px;"
>

<div class="milestone-number">
    CO₂
</div>

<div class="milestone-text">

Material quantities can be translated into embodied
carbon estimates for demolition analysis.

</div>

</td>

</tr>

</table>


</td>

</tr>

</table>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- PROJECT STATUS -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    class="mobile-padding"
    style="
        padding:0 42px 38px 42px;
    "
>

<h2 class="section-title">
    Current project status
</h2>


<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    style="margin-top:18px;"
>

<tr>

<td
    width="50%"
    valign="top"
    style="
        padding:16px;
        background:#f8fafc;
        border:1px solid #e7ebf0;
    "
>

<div
    style="
        font-size:11px;
        font-weight:700;
        color:#8a94a6;
        letter-spacing:.7px;
    "
>

DATA COLLECTION

</div>

<div
    style="
        margin-top:7px;
        font-size:14px;
        font-weight:700;
        color:#17864b;
    "
>

✓ Completed

</div>

</td>


<td
    width="50%"
    valign="top"
    style="
        padding:16px;
        background:#f8fafc;
        border:1px solid #e7ebf0;
        border-left:0;
    "
>

<div
    style="
        font-size:11px;
        font-weight:700;
        color:#8a94a6;
        letter-spacing:.7px;
    "
>

BAG + 3DBAG

</div>

<div
    style="
        margin-top:7px;
        font-size:14px;
        font-weight:700;
        color:#17864b;
    "
>

✓ Completed

</div>

</td>

</tr>


<tr>

<td
    width="50%"
    valign="top"
    style="
        padding:16px;
        background:#f8fafc;
        border:1px solid #e7ebf0;
        border-top:0;
    "
>

<div
    style="
        font-size:11px;
        font-weight:700;
        color:#8a94a6;
        letter-spacing:.7px;
    "
>

MATERIAL ESTIMATION

</div>

<div
    style="
        margin-top:7px;
        font-size:14px;
        font-weight:700;
        color:#17864b;
    "
>

✓ Completed

</div>

</td>


<td
    width="50%"
    valign="top"
    style="
        padding:16px;
        background:#f8fafc;
        border:1px solid #e7ebf0;
        border-left:0;
        border-top:0;
    "
>

<div
    style="
        font-size:11px;
        font-weight:700;
        color:#8a94a6;
        letter-spacing:.7px;
    "
>

EMBODIED CARBON

</div>

<div
    style="
        margin-top:7px;
        font-size:14px;
        font-weight:700;
        color:#17864b;
    "
>

✓ Completed

</div>

</td>

</tr>

</table>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- CLOSING MESSAGE -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    class="mobile-padding"
    style="
        padding:5px 42px 40px 42px;
    "
>

<p
    style="
        margin:0;
        font-size:15px;
        line-height:25px;
        color:#5b6472;
    "
>

This milestone establishes a strong foundation for
DataFuse AI's continued development toward scalable
building material recovery, demolition analysis and
carbon-impact intelligence.

</p>


<p
    style="
        margin:24px 0 0 0;
        font-size:15px;
        line-height:24px;
        color:#4b5563;
    "
>

Regards,<br>

<strong style="color:#111827;">
Sahildahal
</strong>

</p>

</td>

</tr>

</table>


<!-- ================================================= -->
<!-- FOOTER -->
<!-- ================================================= -->

<table
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
>

<tr>

<td
    style="
        background:#f8fafc;
        border-top:1px solid #e8edf3;
        padding:24px 30px;
    "
>

<div class="footer-brand">
    DataFuse<span style="color:#5b8def;">AI</span>
</div>


<p class="footer">

Building intelligence from data,
geometry, materials and carbon.

</p>


<p
    class="footer"
    style="margin-bottom:0;"
>

This is an automated project-update email from
DataFuse AI.

</p>

</td>

</tr>

</table>


</td>

</tr>

</table>

</td>

</tr>

</table>

</body>

</html>
"""


    # =========================================================
    # PLAIN TEXT FALLBACK
    # =========================================================

    plain_text = f"""
DataFuse AI – Project Milestone Update

Hello, {name}

We are excited to share a major milestone in the DataFuse AI project.

The core data pipeline has progressed through:

1. KOOP
   Dutch demolition notices have been collected and structured.

2. PDOK / BAG
   Demolition locations have been matched with BAG building information,
   including PAND identifiers, construction year, building function and
   geometry.

3. 3DBAG
   Three-dimensional building characteristics such as height, volume and
   roof information have been added.

Current dataset:
- 1,081 buildings
- KOOP + BAG + 3DBAG enrichment completed
- Material estimation completed
- Embodied carbon analysis completed

The enriched dataset now provides the foundation for estimating
demolition materials and associated embodied carbon.

Material groups include:
steel, copper, aluminium, wood, concrete, brick, glass,
plastics, insulation and other material groups.

Regards,

Sahildahal

DataFuse AI
Building intelligence from data, geometry, materials and carbon.

This is an automated project-update email from DataFuse AI.
"""


    # =========================================================
    # SET EMAIL CONTENT
    # =========================================================

    message.set_content(
        plain_text.strip()
    )

    message.add_alternative(
        html_content,
        subtype="html"
    )


    # =========================================================
    # ADD INLINE HERO IMAGE
    # =========================================================

    if HERO_IMAGE.exists():

        try:

            with open(HERO_IMAGE, "rb") as image_file:

                image_data = image_file.read()

            # Determine MIME subtype from extension
            extension = HERO_IMAGE.suffix.lower()

            if extension in [".jpg", ".jpeg"]:
                maintype = "image"
                subtype = "jpeg"

            elif extension == ".png":
                maintype = "image"
                subtype = "png"

            elif extension == ".gif":
                maintype = "image"
                subtype = "gif"

            elif extension == ".webp":
                maintype = "image"
                subtype = "webp"

            else:

                logger.warning(
                    "EMAIL_IMAGE_UNSUPPORTED | path=%s",
                    HERO_IMAGE
                )

                maintype = None
                subtype = None


            if maintype and subtype:

                message.get_payload()[-1].add_related(
                    image_data,
                    maintype=maintype,
                    subtype=subtype,
                    cid=hero_cid_value,
                    filename=HERO_IMAGE.name
                )

                logger.info(
                    "EMAIL_INLINE_IMAGE_ATTACHED | path=%s | cid=%s",
                    HERO_IMAGE,
                    hero_cid_value
                )

        except Exception as exc:

            logger.error(
                "EMAIL_IMAGE_FAILED | path=%s | "
                "error_type=%s | error=%s",
                HERO_IMAGE,
                type(exc).__name__,
                str(exc)
            )

    else:

        logger.warning(
            "EMAIL_IMAGE_NOT_FOUND | path=%s",
            HERO_IMAGE
        )


    # =========================================================
    # SEND EMAIL
    # =========================================================

    try:

        await aiosmtplib.send(
            message,
            hostname=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_USERNAME,
            password=settings.EMAIL_PASSWORD,
            start_tls=True
        )


        # =====================================================
        # SUCCESS LOG
        # =====================================================

        logger.info(
            "EMAIL_SENT | from=%s | to=%s | name=%s",
            sender_email,
            email,
            name
        )


        return {
            "success": True,
            "status": 200,
            "message": "Email sent successfully",
            "data": {
                "email": email,
                "name": name
            },
            "error": None
        }


    except Exception as exc:

        # =====================================================
        # FAILURE LOG
        # =====================================================

        logger.error(
            "EMAIL_FAILED | from=%s | to=%s | name=%s | "
            "error_type=%s | error=%s",
            sender_email,
            email,
            name,
            type(exc).__name__,
            str(exc)
        )


        raise HTTPException(
            status_code=500,
            detail="Failed to send email"
        )
