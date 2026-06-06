from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
import httpx
import os
import urllib.parse
from loguru import logger
import database as db

router = APIRouter(prefix="/auth", tags=["auth"])

META_CLIENT_ID = os.getenv("META_CLIENT_ID", "")
META_CLIENT_SECRET = os.getenv("META_CLIENT_SECRET", "")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "")

@router.get("/meta")
async def meta_login(platform: str = "threads"):
    """Redirect user to Meta Graph API OAuth login page"""
    if not META_CLIENT_ID:
        raise HTTPException(400, "META_CLIENT_ID environment variable not set")
    
    # Configure scopes depending on platform
    if platform == "threads":
        scopes = "threads_basic,threads_content_publish"
        auth_url = (
            "https://threads.net/oauth/authorize"
            f"?client_id={META_CLIENT_ID}"
            f"&redirect_uri={urllib.parse.quote(META_REDIRECT_URI)}"
            f"&scope={scopes}"
            "&response_type=code"
            "&state=threads"
        )
    else:
        scopes = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"
        auth_url = (
            "https://www.facebook.com/v20.0/dialog/oauth"
            f"?client_id={META_CLIENT_ID}"
            f"&redirect_uri={urllib.parse.quote(META_REDIRECT_URI)}"
            f"&scope={scopes}"
            "&response_type=code"
            "&state=instagram"
        )
        
    return RedirectResponse(auth_url)

@router.get("/callback")
async def meta_callback(request: Request, code: str = None, error: str = None, state: str = "threads"):
    """Handle Meta OAuth authorization code callback"""
    if error:
        logger.error(f"[oauth] Meta OAuth error callback: {error}")
        return HTMLResponse(content=f"<h3>Ошибка авторизации: {error}</h3>", status_code=400)
    if not code:
        raise HTTPException(400, "Authorization code is required")
        
    # Exchange code for token
    from webapp import get_current_user
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(content="<h3>Ошибка: Вы должны быть авторизованы в боте</h3>", status_code=401)
        
    try:
        async with httpx.AsyncClient() as client:
            if state == "threads":
                url = "https://graph.threads.net/oauth/access_token"
                payload = {
                    "client_id": META_CLIENT_ID,
                    "client_secret": META_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "redirect_uri": META_REDIRECT_URI,
                    "code": code
                }
                r = await client.post(url, data=payload)
                r.raise_for_status()
                data = r.json()
                access_token = data.get("access_token")
                threads_user_id = data.get("user_id")
                
                # Fetch profile info
                profile_url = "https://graph.threads.net/me"
                params = {
                    "fields": "id,username,threads_profile_picture_url",
                    "access_token": access_token
                }
                r_prof = await client.get(profile_url, params=params)
                r_prof.raise_for_status()
                profile = r_prof.json()
                username = profile.get("username", f"threads_{threads_user_id}")
                
                await db.add_social_account(
                    user_id=user["id"],
                    platform="threads",
                    platform_user_id=str(threads_user_id),
                    username=username,
                    access_token=access_token,
                    token_expires_at=None,
                    settings="{}"
                )
            else:
                url = "https://graph.facebook.com/v20.0/oauth/access_token"
                params = {
                    "client_id": META_CLIENT_ID,
                    "client_secret": META_CLIENT_SECRET,
                    "redirect_uri": META_REDIRECT_URI,
                    "code": code
                }
                r = await client.get(url, params=params)
                r.raise_for_status()
                data = r.json()
                access_token = data.get("access_token")
                
                # Get Instagram Business Accounts connected to Pages
                pages_url = "https://graph.facebook.com/v20.0/me/accounts"
                r_pages = await client.get(pages_url, params={"access_token": access_token})
                r_pages.raise_for_status()
                pages = r_pages.json().get("data", [])
                
                added_accounts = []
                for page in pages:
                    page_id = page.get("id")
                    page_token = page.get("access_token")
                    
                    ig_url = f"https://graph.facebook.com/v20.0/{page_id}"
                    r_ig = await client.get(ig_url, params={"fields": "instagram_business_account{id,username,profile_picture_url}", "access_token": page_token})
                    r_ig.raise_for_status()
                    ig_data = r_ig.json().get("instagram_business_account")
                    if ig_data:
                        ig_id = ig_data.get("id")
                        ig_username = ig_data.get("username")
                        
                        await db.add_social_account(
                            user_id=user["id"],
                            platform="instagram",
                            platform_user_id=str(ig_id),
                            username=ig_username,
                            access_token=page_token,
                            settings="{}"
                        )
                        added_accounts.append(ig_username)
                        
                if not added_accounts:
                    return HTMLResponse(content="<h3>Авторизация прошла успешно, но не найдено привязанных Instagram Business аккаунтов. Убедитесь, что ваш Instagram аккаунт привязан к Facebook Page.</h3>")
                    
        return HTMLResponse(content="""
            <html>
            <head>
                <script>
                    alert("✅ Аккаунт успешно добавлен!");
                    window.location.href = "/dashboard";
                </script>
            </head>
            <body>
                <h3>Перенаправление...</h3>
            </body>
            </html>
        """)
    except Exception as e:
        logger.error(f"[oauth] Exchange failed: {e}")
        return HTMLResponse(content=f"<h3>Ошибка авторизации: {str(e)}</h3>", status_code=500)
