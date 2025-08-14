# naver_blog_automation.py - Core blog posting automation
import os
import time
import pyperclip
import structlog
from typing import Optional, Callable
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
    WebDriverException,
    NoSuchElementException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logger = structlog.get_logger()

class BlogPoster:
    """
    Naver blog posting automation class
    """
    
    def __init__(
        self, 
        naver_id: str, 
        naver_password: str, 
        task_id: str,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        self.naver_id = naver_id
        self.naver_password = naver_password
        self.task_id = task_id
        self.progress_callback = progress_callback
        self.driver = None
        self.wait = None
        
        logger.info("BlogPoster initialized", task_id=task_id, naver_id=naver_id)
    
    def _update_progress(self, progress: int, status: str):
        """Update task progress"""
        logger.info("Progress update", 
                   task_id=self.task_id, 
                   progress=progress, 
                   status=status)
        
        if self.progress_callback:
            self.progress_callback(progress, status)
    
    def _init_driver(self) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with optimized settings"""
        try:
            self._update_progress(15, "Chrome 드라이버 초기화 중...")
            
            opts = Options()
            
            # Headless mode for server environment
            opts.add_argument("--headless")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            
            # Fix for "user data directory already in use" error
            import tempfile
            import uuid
            import os
            import shutil
            
            # Create unique temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f"chrome_user_data_{uuid.uuid4().hex[:8]}_")
            
            # Ensure directory is writable
            os.chmod(temp_dir, 0o755)
            
            # Clean up any existing Chrome processes (kill zombies)
            try:
                import subprocess
                subprocess.run(['pkill', '-f', 'chrome'], check=False, capture_output=True)
                subprocess.run(['pkill', '-f', 'chromium'], check=False, capture_output=True)
            except:
                pass
            
            opts.add_argument(f"--user-data-dir={temp_dir}")
            
            # Additional isolation arguments
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-default-apps")
            
            # Even more aggressive Chrome options for cloud environments
            opts.add_argument("--remote-debugging-port=0")  # Disable remote debugging
            opts.add_argument("--disable-web-security")
            opts.add_argument("--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer")
            opts.add_argument("--run-all-compositor-stages-before-draw")
            opts.add_argument("--disable-background-networking")
            opts.add_argument("--disable-background-mode")
            opts.add_argument("--disable-client-side-phishing-detection")
            opts.add_argument("--disable-sync")
            opts.add_argument("--metrics-recording-only")
            opts.add_argument("--no-pings")
            opts.add_argument("--password-store=basic")
            opts.add_argument("--use-mock-keychain")
            
            # Additional cloud environment fixes
            opts.add_argument("--disable-background-timer-throttling")
            opts.add_argument("--disable-backgrounding-occluded-windows")
            opts.add_argument("--disable-renderer-backgrounding")
            opts.add_argument("--disable-features=VizDisplayCompositor")
            opts.add_argument("--disable-ipc-flooding-protection")
            opts.add_argument("--single-process")  # Render cloud environment
            
            # Performance optimizations
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-plugins")
            opts.add_argument("--disable-images")
            # Remove --disable-javascript as Naver blog needs JS
            
            # Security and stability
            opts.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(30)
            
            logger.info("Chrome driver initialized successfully", 
                       task_id=self.task_id, 
                       user_data_dir=temp_dir)
            return driver
            
        except Exception as e:
            logger.error("Failed to initialize Chrome driver", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"브라우저 초기화 실패: {str(e)}")
    
    def _naver_login(self):
        """Login to Naver"""
        try:
            self._update_progress(25, "네이버 로그인 중...")
            
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)
            
            # ID input
            id_input = self.wait.until(EC.presence_of_element_located((By.ID, "id")))
            id_input.clear()
            pyperclip.copy(self.naver_id)
            id_input.send_keys(Keys.CONTROL, "v")
            time.sleep(0.5)
            
            # Password input
            pw_input = self.driver.find_element(By.ID, "pw")
            pw_input.clear()
            pyperclip.copy(self.naver_password)
            pw_input.send_keys(Keys.CONTROL, "v")
            time.sleep(0.5)
            
            # Login button
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            time.sleep(3)
            
            # Check if login was successful
            if "nid.naver.com" in self.driver.current_url:
                raise Exception("로그인 실패 - 아이디/비밀번호를 확인해주세요")
            
            logger.info("Naver login successful", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Naver login failed", task_id=self.task_id, error=str(e))
            raise Exception(f"네이버 로그인 실패: {str(e)}")
    
    def _navigate_to_blog_write(self):
        """Navigate to blog write page"""
        try:
            self._update_progress(40, "블로그 글쓰기 페이지로 이동 중...")
            
            self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
            time.sleep(3)
            
            # Switch to main frame
            iframe = self.wait.until(EC.presence_of_element_located((By.ID, "mainFrame")))
            self.driver.switch_to.frame(iframe)
            
            logger.info("Navigated to blog write page", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Failed to navigate to blog write page", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글쓰기 페이지 이동 실패: {str(e)}")
    
    def _write_blog_content(self, title: str, content: str):
        """Write blog title and content"""
        try:
            self._update_progress(60, "블로그 글 작성 중...")
            
            # Title input
            title_input = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "se-input")))
            title_input.clear()
            pyperclip.copy(title)
            title_input.send_keys(Keys.CONTROL, "v")
            time.sleep(1)
            
            # Content input
            content_area = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "se-content")))
            content_area.click()
            time.sleep(1)
            
            pyperclip.copy(content)
            content_area.send_keys(Keys.CONTROL, "v")
            time.sleep(2)
            
            logger.info("Blog content written", 
                       task_id=self.task_id, 
                       title_length=len(title),
                       content_length=len(content))
            
        except Exception as e:
            logger.error("Failed to write blog content", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글 작성 실패: {str(e)}")
    
    def _publish_blog(self):
        """Publish the blog post"""
        try:
            self._update_progress(80, "블로그 글 발행 중...")
            
            # Find and click publish button
            publish_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "publish_btn")))
            publish_btn.click()
            time.sleep(2)
            
            # Handle any confirmation dialogs
            try:
                confirm_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '발행')]")
                confirm_btn.click()
                time.sleep(2)
            except NoSuchElementException:
                pass  # No confirmation dialog
            
            logger.info("Blog post published successfully", task_id=self.task_id)
            
        except Exception as e:
            logger.error("Failed to publish blog post", 
                        task_id=self.task_id, 
                        error=str(e))
            raise Exception(f"블로그 글 발행 실패: {str(e)}")
    
    def post_blog(self, title: str, content: str, category: Optional[str] = None, tags: Optional[str] = None) -> dict:
        """
        Main method to post a blog entry
        """
        try:
            self._update_progress(5, "작업 시작...")
            
            # Initialize driver
            self.driver = self._init_driver()
            self.wait = WebDriverWait(self.driver, 15)
            
            # Login to Naver
            self._naver_login()
            
            # Navigate to blog write page
            self._navigate_to_blog_write()
            
            # Write content
            self._write_blog_content(title, content)
            
            # Publish blog
            self._publish_blog()
            
            self._update_progress(100, "블로그 포스팅 완료!")
            
            result = {
                "success": True,
                "message": "네이버 블로그 포스팅이 성공적으로 완료되었습니다.",
                "title": title,
                "content_length": len(content),
                "posted_at": time.strftime("%Y-%m-%d %H:%M:%S")
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
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("Chrome driver cleaned up", task_id=self.task_id)
                except Exception as cleanup_error:
                    logger.warning("Failed to cleanup driver", 
                                  task_id=self.task_id, 
                                  error=str(cleanup_error))
                
                # Force kill any remaining Chrome processes
                try:
                    import subprocess
                    subprocess.run(['pkill', '-f', 'chrome'], check=False, capture_output=True)
                    subprocess.run(['pkill', '-f', 'chromium'], check=False, capture_output=True)
                except:
                    pass