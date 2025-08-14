# naver_blog_puppeteer.py - Puppeteer-based blog automation
import asyncio
import structlog
from typing import Optional, Callable
from pyppeteer import launch
from pyppeteer.errors import TimeoutError as PuppeteerTimeoutError

logger = structlog.get_logger()

class PuppeteerBlogPoster:
    """
    Naver blog posting automation using Puppeteer (more stable for cloud)
    """
    
    def __init__(
        self, 
        naver_id: str, 
        task_id: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        self.naver_id = naver_id
        self.task_id = task_id
        self.progress_callback = progress_callback
        self.browser = None
        self.page = None
        
        logger.info("PuppeteerBlogPoster initialized", task_id=task_id, naver_id=naver_id)
    
    def _update_progress(self, progress: int, status: str):
        """Update task progress"""
        logger.info("Progress update", 
                   task_id=self.task_id, 
                   progress=progress, 
                   status=status)
        
        if self.progress_callback:
            self.progress_callback(progress, status)
    
    async def _init_browser(self):
        """Initialize Puppeteer browser"""
        try:
            self._update_progress(15, "브라우저 초기화 중...")
            
            # Puppeteer launch options optimized for cloud environments
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--window-size=1920,1080'
            ]
            
            self.browser = await launch(
                headless=True,
                args=browser_args,
                ignoreHTTPSErrors=True,
                autoClose=True,
                timeout=30000,
                dumpio=False
            )
            
            self.page = await self.browser.newPage()
            
            # Set user agent and viewport
            await self.page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            await self.page.setViewport({'width': 1920, 'height': 1080})
            
            logger.info("Puppeteer browser initialized successfully", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Failed to initialize Puppeteer browser", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"브라우저 초기화 실패: {str(e)}")
    
    async def _naver_login_manual(self):
        """Navigate to manual login page and wait"""
        try:
            self._update_progress(25, "네이버 로그인 페이지로 이동...")
            
            await self.page.goto("https://nid.naver.com/nidlogin.login", {'waitUntil': 'networkidle0'})
            
            # Fill in the username
            await self.page.waitForSelector('#id', {'timeout': 10000})
            await self.page.type('#id', self.naver_id)
            
            self._update_progress(30, f"'{self.naver_id}' 계정으로 수동 로그인 대기 중...")
            
            # Manual login instructions
            manual_login_msg = f"""
            ✅ 네이버 로그인 페이지가 열렸습니다.
            📋 사용자 ID '{self.naver_id}'가 입력되었습니다.
            
            🔐 다음 단계를 수행하세요:
            1. 비밀번호를 직접 입력하세요
            2. 필요시 보안 인증을 완료하세요 (SMS, OTP 등)
            3. '로그인 유지' 체크 (권장)
            4. 로그인 버튼을 클릭하세요
            
            ⏳ 로그인이 완료될 때까지 대기합니다... (최대 5분)
            """
            logger.info("Manual login required", task_id=self.task_id, instructions=manual_login_msg)
            
            # Wait for successful login (redirect away from login page)
            login_timeout = 300000  # 5 minutes
            
            try:
                await self.page.waitForFunction(
                    '!window.location.href.includes("nid.naver.com")', 
                    {'timeout': login_timeout}
                )
                
                self._update_progress(40, "로그인 성공 ✅")
                logger.info("Manual login successful", task_id=self.task_id)
                
            except PuppeteerTimeoutError:
                raise Exception("로그인 시간 초과 - 5분 내에 로그인을 완료해주세요")
            
        except Exception as e:
            logger.error("Manual login failed", task_id=self.task_id, error=str(e))
            raise Exception(f"로그인 실패: {str(e)}")
    
    async def _navigate_to_blog_write(self):
        """Navigate to blog write page"""
        try:
            self._update_progress(50, "블로그 글쓰기 페이지로 이동...")
            
            await self.page.goto("https://blog.naver.com/GoBlogWrite.naver", 
                                {'waitUntil': 'networkidle0', 'timeout': 30000})
            
            # Wait for main frame to load
            await self.page.waitForSelector('#mainFrame', {'timeout': 15000})
            
            # Switch to iframe
            frames = await self.page.frames()
            main_frame = None
            for frame in frames:
                if 'mainFrame' in frame.name or 'postframe' in frame.url:
                    main_frame = frame
                    break
            
            if not main_frame:
                raise Exception("메인 프레임을 찾을 수 없습니다")
            
            self.page = main_frame
            logger.info("Navigated to blog write page", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Failed to navigate to blog write page", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글쓰기 페이지 이동 실패: {str(e)}")
    
    async def _write_blog_content(self, title: str, content: str):
        """Write blog title and content"""
        try:
            self._update_progress(70, "블로그 글 작성 중...")
            
            # Title input
            await self.page.waitForSelector('.se-input', {'timeout': 10000})
            await self.page.click('.se-input')
            await self.page.evaluate('(selector) => document.querySelector(selector).value = ""', '.se-input')
            await self.page.type('.se-input', title)
            
            # Content input
            await self.page.waitForSelector('.se-content', {'timeout': 10000})
            await self.page.click('.se-content')
            await asyncio.sleep(1)
            
            # Type content directly
            await self.page.type('.se-content', content)
            await asyncio.sleep(2)
            
            logger.info("Blog content written", 
                       task_id=self.task_id, 
                       title_length=len(title),
                       content_length=len(content))
            
        except Exception as e:
            logger.error("Failed to write blog content", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글 작성 실패: {str(e)}")
    
    async def _publish_blog(self):
        """Publish the blog post"""
        try:
            self._update_progress(90, "블로그 글 발행 중...")
            
            # Find and click publish button
            await self.page.waitForSelector('.publish_btn', {'timeout': 10000})
            await self.page.click('.publish_btn')
            await asyncio.sleep(2)
            
            # Handle confirmation dialog if exists
            try:
                await self.page.waitForSelector('button:contains("발행")', {'timeout': 3000})
                await self.page.click('button:contains("발행")')
                await asyncio.sleep(2)
            except:
                pass  # No confirmation dialog
            
            logger.info("Blog post published successfully", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Failed to publish blog post", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글 발행 실패: {str(e)}")
    
    async def post_blog(self, title: str, content: str, category: Optional[str] = None, tags: Optional[str] = None) -> dict:
        """
        Main method to post a blog entry using Puppeteer
        """
        try:
            self._update_progress(5, "작업 시작...")
            
            # Initialize browser
            await self._init_browser()
            
            # Manual login process
            await self._naver_login_manual()
            
            # Navigate to blog write page
            await self._navigate_to_blog_write()
            
            # Write content
            await self._write_blog_content(title, content)
            
            # Publish blog
            await self._publish_blog()
            
            self._update_progress(100, "블로그 포스팅 완료! ✅")
            
            result = {
                "success": True,
                "message": "네이버 블로그 포스팅이 성공적으로 완료되었습니다.",
                "title": title,
                "content_length": len(content),
                "automation_engine": "Puppeteer",
                "posted_at": asyncio.get_event_loop().time()
            }
            
            logger.info("Blog posting completed successfully", 
                       task_id=self.task_id, 
                       result=result)
            
            return result
            
        except Exception as e:
            logger.error("Blog posting failed", task_id=self.task_id, error=str(e))
            raise e
            
        finally:
            # Always cleanup
            if self.browser:
                try:
                    await self.browser.close()
                    logger.info("Puppeteer browser cleaned up", task_id=self.task_id)
                except Exception as cleanup_error:
                    logger.warning("Failed to cleanup browser", 
                                  task_id=self.task_id, 
                                  error=str(cleanup_error))


# Async wrapper for compatibility with existing sync code
def post_blog_with_puppeteer(naver_id: str, task_id: str, title: str, content: str, 
                            category: Optional[str] = None, tags: Optional[str] = None,
                            progress_callback: Optional[Callable[[int, str], None]] = None) -> dict:
    """
    Synchronous wrapper for the async Puppeteer blog poster
    """
    poster = PuppeteerBlogPoster(naver_id, task_id, progress_callback)
    
    # Run the async method
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            poster.post_blog(title, content, category, tags)
        )
        return result
    finally:
        loop.close()