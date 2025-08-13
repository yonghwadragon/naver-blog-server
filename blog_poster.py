# blog_poster.py - Blog posting class for FastAPI immediate execution
import os
import time
import structlog
import uuid
import tempfile
import shutil
from typing import Optional
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
    Naver blog posting automation class for FastAPI
    """
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.user_data_dir = None
        self.session_id = str(uuid.uuid4())
        
    def _init_driver(self, account_id: str) -> webdriver.Chrome:
        """Initialize Chrome WebDriver with isolated profile per account"""
        try:
            logger.info("Initializing Chrome driver with isolated profile", 
                       account_id=account_id, session_id=self.session_id)
            
            # Create isolated user data directory for this account
            self.user_data_dir = tempfile.mkdtemp(prefix=f'naver-{account_id}-{self.session_id[:8]}-')
            logger.info("Created isolated profile directory", user_data_dir=self.user_data_dir)
            
            opts = Options()
            
            # Headless mode for server environment
            opts.add_argument("--headless")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            
            # Isolated user profile for security
            opts.add_argument(f"--user-data-dir={self.user_data_dir}")
            opts.add_argument("--disable-web-security")
            opts.add_argument("--disable-features=VizDisplayCompositor")
            
            # Performance optimizations
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-plugins")
            opts.add_argument("--disable-images")
            # JavaScript enabled for Naver login functionality
            
            # Security and stability
            opts.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=opts)
            driver.set_page_load_timeout(30)
            
            logger.info("Chrome driver initialized successfully with isolated profile")
            return driver
            
        except Exception as e:
            logger.error("Failed to initialize Chrome driver", error=str(e))
            self._cleanup_profile()  # Clean up on failure
            raise Exception(f"브라우저 초기화 실패: {str(e)}")
    
    def _cleanup_profile(self):
        """Clean up the isolated user profile directory"""
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir, ignore_errors=True)
                logger.info("Cleaned up profile directory", user_data_dir=self.user_data_dir)
            except Exception as e:
                logger.warning("Failed to clean up profile directory", 
                              user_data_dir=self.user_data_dir, error=str(e))
            finally:
                self.user_data_dir = None
    
    def _naver_login(self, naver_id: str, naver_password: str):
        """Login to Naver"""
        try:
            logger.info("Starting Naver login", naver_id=naver_id)
            
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(2)
            
            # ID input
            id_input = self.wait.until(EC.presence_of_element_located((By.ID, "id")))
            id_input.clear()
            id_input.send_keys(naver_id)
            time.sleep(0.5)
            
            # Password input
            pw_input = self.driver.find_element(By.ID, "pw")
            pw_input.clear()
            pw_input.send_keys(naver_password)
            time.sleep(0.5)
            
            # Login button
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            time.sleep(3)
            
            # Check if login was successful
            if "nid.naver.com" in self.driver.current_url:
                raise Exception("로그인 실패 - 아이디/비밀번호를 확인해주세요")
            
            logger.info("Naver login successful")
            
        except Exception as e:
            logger.error("Naver login failed", error=str(e))
            raise Exception(f"네이버 로그인 실패: {str(e)}")
    
    def _navigate_to_blog_write(self):
        """Navigate to blog write page"""
        try:
            logger.info("Navigating to blog write page")
            
            self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
            time.sleep(3)
            
            # Switch to main frame
            iframe = self.wait.until(EC.presence_of_element_located((By.ID, "mainFrame")))
            self.driver.switch_to.frame(iframe)
            
            logger.info("Navigated to blog write page successfully")
            
        except Exception as e:
            logger.error("Failed to navigate to blog write page", error=str(e))
            raise Exception(f"블로그 글쓰기 페이지 이동 실패: {str(e)}")
    
    def _write_blog_content(self, title: str, content: str):
        """Write blog title and content"""
        try:
            logger.info("Writing blog content", title_length=len(title), content_length=len(content))
            
            # Title input
            title_input = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "se-input")))
            title_input.clear()
            title_input.send_keys(title)
            time.sleep(1)
            
            # Content input
            content_area = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "se-content")))
            content_area.click()
            time.sleep(1)
            
            content_area.send_keys(content)
            time.sleep(2)
            
            logger.info("Blog content written successfully")
            
        except Exception as e:
            logger.error("Failed to write blog content", error=str(e))
            raise Exception(f"블로그 글 작성 실패: {str(e)}")
    
    def _publish_blog(self):
        """Publish the blog post"""
        try:
            logger.info("Publishing blog post")
            
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
            
            logger.info("Blog post published successfully")
            
        except Exception as e:
            logger.error("Failed to publish blog post", error=str(e))
            raise Exception(f"블로그 글 발행 실패: {str(e)}")
    
    def post_to_naver_blog(self, post_data: dict, naver_account: dict) -> dict:
        """
        Main method to post a blog entry to Naver blog with security isolation
        """
        account_id = naver_account.get("id", "unknown")
        
        try:
            logger.info("Starting blog posting task with isolated session", 
                       title=post_data.get("title"), 
                       naver_id=account_id,
                       session_id=self.session_id)
            
            # Initialize driver with isolated profile
            self.driver = self._init_driver(account_id)
            self.wait = WebDriverWait(self.driver, 15)
            
            # Login to Naver
            self._naver_login(naver_account["id"], naver_account["password"])
            
            # Navigate to blog write page
            self._navigate_to_blog_write()
            
            # Write content
            self._write_blog_content(post_data["title"], post_data["content"])
            
            # Publish blog
            self._publish_blog()
            
            result = {
                "success": True,
                "message": "네이버 블로그 포스팅이 성공적으로 완료되었습니다.",
                "title": post_data["title"],
                "content_length": len(post_data["content"]),
                "posted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": self.session_id
            }
            
            logger.info("Blog posting completed successfully", result=result)
            return result
            
        except Exception as e:
            logger.error("Blog posting failed", 
                        error=str(e), 
                        account_id=account_id, 
                        session_id=self.session_id)
            raise e
            
        finally:
            # Always cleanup browser and profile
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("Chrome driver cleaned up")
                except Exception as cleanup_error:
                    logger.warning("Failed to cleanup driver", error=str(cleanup_error))
            
            # Clean up isolated profile directory
            self._cleanup_profile()