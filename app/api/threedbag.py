# app/api/threedbag.py

import requests

from fastapi import APIRouter

from app.api.pipeline import response


router = APIRouter(
    prefix="/3dbag",
    tags=["3DBAG"]
)


BASE_URL = "https://api.3dbag.nl/collections/pand/items"
TIMEOUT = 30


def get_3dbag_building(pand_id: str):

    pand_id = str(pand_id).strip()

    if not pand_id:
        return None

    full_3dbag_id = f"NL.IMBAG.Pand.{pand_id}"

    url = f"{BASE_URL}/{full_3dbag_id}"

    try:

        result = requests.get(
            url,
            headers={
                "Accept": "application/json"
            },
            timeout=TIMEOUT
        )

        if result.status_code != 200:
            return {
                "error": "3DBAG API returned HTTP "
                f"{result.status_code}"
            }

        data = result.json()

    except requests.RequestException as exc:

        return {
            "error": f"3DBAG request failed: {str(exc)}"
        }

    except ValueError:

        return {
            "error": "3DBAG returned invalid JSON"
        }

    # --------------------------------------------------------
    # CityJSONFeature
    # --------------------------------------------------------

    feature = data.get("feature")

    if not isinstance(feature, dict):

        return {
            "error": "3DBAG response does not contain feature"
        }

    city_objects = feature.get("CityObjects")

    if not isinstance(city_objects, dict):

        return {
            "error": "3DBAG response does not contain CityObjects"
        }

    # --------------------------------------------------------
    # Find BAG Building
    # --------------------------------------------------------

    building = city_objects.get(full_3dbag_id)

    if not isinstance(building, dict):

        return {
            "error": "3DBAG Building not found",
            "3dbag_id": full_3dbag_id
        }

    if building.get("type") != "Building":

        return {
            "error": "3DBAG object is not a Building",
            "3dbag_id": full_3dbag_id
        }

    attributes = building.get(
        "attributes",
        {}
    )

    if not isinstance(attributes, dict):

        return {
            "error": "3DBAG Building has no attributes",
            "3dbag_id": full_3dbag_id
        }

    # --------------------------------------------------------
    # Extract 3DBAG attributes
    # --------------------------------------------------------

    return {

        "3dbag_id": full_3dbag_id,

        "bouwjaar": attributes.get(
            "oorspronkelijkbouwjaar"
        ),

        "status": attributes.get(
            "status"
        ),

        "bouwlagen": attributes.get(
            "b3_bouwlagen"
        ),

        "dak_type": attributes.get(
            "b3_dak_type"
        ),

        "extrusie": attributes.get(
            "b3_extrusie"
        ),

        "h_maaiveld": attributes.get(
            "b3_h_maaiveld"
        ),

        "h_dak_min": attributes.get(
            "b3_h_dak_min"
        ),

        "h_dak_max": attributes.get(
            "b3_h_dak_max"
        ),

        "opp_grond": attributes.get(
            "b3_opp_grond"
        ),

        "opp_buitenmuur": attributes.get(
            "b3_opp_buitenmuur"
        ),

        "opp_scheidingsmuur": attributes.get(
            "b3_opp_scheidingsmuur"
        ),

        "opp_dak_plat": attributes.get(
            "b3_opp_dak_plat"
        ),

        "opp_dak_schuin": attributes.get(
            "b3_opp_dak_schuin"
        ),

        "volume_lod12": attributes.get(
            "b3_volume_lod12"
        ),

        "volume_lod13": attributes.get(
            "b3_volume_lod13"
        ),

        "volume_lod22": attributes.get(
            "b3_volume_lod22"
        ),

        "kwaliteitsindicator": attributes.get(
            "b3_kwaliteitsindicator"
        ),

        "pw_bron": attributes.get(
            "b3_pw_bron"
        ),

        "pw_datum": attributes.get(
            "b3_pw_datum"
        ),

        "fid": attributes.get(
            "fid"
        ),

        "identificatie": attributes.get(
            "identificatie"
        )
    }


# ============================================================
# GET /3dbag/{pand_id}
# ============================================================

@router.get("/{pand_id}")
def get_3dbag(pand_id: str):

    result = get_3dbag_building(pand_id)

    if result is None:

        return response(
            success=False,
            status=404,
            message="3DBAG building not found",
            data=None,
            error={
                "code": "3DBAG_NOT_FOUND",
                "details": pand_id
            }
        )

    if "error" in result:

        return response(
            success=False,
            status=502,
            message="3DBAG lookup failed",
            data=None,
            error={
                "code": "3DBAG_LOOKUP_FAILED",
                "details": result
            }
        )

    return response(
        success=True,
        status=200,
        message="3DBAG building retrieved successfully",
        data=result,
        error=None
    )