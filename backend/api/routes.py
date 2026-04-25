"""API ルート定義（仕様 §12）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas import ErrorResponse, SetupRequest, SetupResponse
from backend.core import folder_setup


router = APIRouter(prefix='/api')


@router.post(
    '/setup',
    response_model=SetupResponse,
    responses={400: {'model': ErrorResponse}, 404: {'model': ErrorResponse}},
)
def api_setup(req: SetupRequest) -> SetupResponse:
    """ルートフォルダを検証・初期化する。"""
    try:
        root = folder_setup.normalize_root_path(req.root_path)
        result = folder_setup.setup_root(root)
        return SetupResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail={
            'error': 'FileNotFoundError',
            'message': str(e),
            'detail': req.root_path,
        })
    except NotADirectoryError as e:
        raise HTTPException(status_code=400, detail={
            'error': 'NotADirectoryError',
            'message': str(e),
            'detail': req.root_path,
        })
    except OSError as e:
        raise HTTPException(status_code=500, detail={
            'error': type(e).__name__,
            'message': 'フォルダ初期化中にエラーが発生しました',
            'detail': str(e),
        })
