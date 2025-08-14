# blog_poster.py - Blog posting class for FastAPI immediate execution
import os
import time
import structlog
import uuid
import tempfile
import shutil
from typing import Optional

# Import both Selenium and Puppeteer for fallback support
try:
    from naver_blog_puppeteer import post_blog_with_puppeteer
    PUPPETEER_AVAILABLE = True
    logger = structlog.get_logger()
    logger.info("Puppeteer automation module loaded successfully")
except ImportError as e:
    PUPPETEER_AVAILABLE = False
    logger = structlog.get_logger()
    logger.warning("Puppeteer not available, falling back to Selenium", error=str(e))

# Selenium imports (fallback)
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
            
            # Clean up any existing profile directory first
            self._cleanup_profile()
            
            # Create unique isolated user data directory
            import hashlib
            unique_id = hashlib.md5(f"{account_id}-{self.session_id}-{time.time()}".encode()).hexdigest()[:8]
            self.user_data_dir = tempfile.mkdtemp(prefix=f'naver-{unique_id}-')
            
            # Ensure directory is empty and accessible
            if os.path.exists(self.user_data_dir):
                try:
                    shutil.rmtree(self.user_data_dir, ignore_errors=True)
                except:
                    pass
            os.makedirs(self.user_data_dir, exist_ok=True)
            
            logger.info("Created isolated profile directory", user_data_dir=self.user_data_dir)
            
            opts = Options()
            
            # GUI mode for user interaction - headless disabled
            # opts.add_argument("--headless")  # Disabled for manual login
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            
            # Isolated user profile for security
            opts.add_argument(f"--user-data-dir={self.user_data_dir}")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--disable-web-security")
            opts.add_argument("--disable-features=VizDisplayCompositor")
            opts.add_argument("--disable-backgrounding-occluded-windows")
            opts.add_argument("--disable-renderer-backgrounding")
            
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
                # Force close any handles before cleanup
                import gc
                gc.collect()
                
                # Multiple cleanup attempts
                for attempt in range(3):
                    try:
                        shutil.rmtree(self.user_data_dir, ignore_errors=True)
                        if not os.path.exists(self.user_data_dir):
                            logger.info("Cleaned up profile directory", user_data_dir=self.user_data_dir)
                            break
                        time.sleep(0.5)  # Wait between attempts
                    except Exception as e:
                        logger.warning(f"Cleanup attempt {attempt + 1} failed", 
                                     user_data_dir=self.user_data_dir, error=str(e))
                        if attempt == 2:  # Last attempt
                            logger.error("Final cleanup attempt failed", 
                                       user_data_dir=self.user_data_dir, error=str(e))
                            
            except Exception as e:
                logger.warning("Failed to clean up profile directory", 
                              user_data_dir=self.user_data_dir, error=str(e))
            finally:
                self.user_data_dir = None
    
    def _cleanup_all_temp_profiles(self):
        """Clean up any leftover temporary profile directories"""
        try:
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                if item.startswith('naver-') and os.path.isdir(os.path.join(temp_dir, item)):
                    try:
                        shutil.rmtree(os.path.join(temp_dir, item), ignore_errors=True)
                        logger.info("Cleaned up leftover profile", profile_dir=item)
                    except:
                        pass  # Ignore cleanup errors for old profiles
        except Exception as e:
            logger.warning("Failed to cleanup leftover profiles", error=str(e))
    
    def _wait_for_manual_login(self):
        """Wait for user to manually login to Naver"""
        try:
            logger.info("Opening Naver login page for manual login")
            
            # Navigate to Naver login page
            self.driver.get("https://nid.naver.com/nidlogin.login")
            
            logger.info("Please login manually in the browser window...")
            print("\n" + "="*60)
            print("🌐 브라우저 창이 열렸습니다!")
            print("📝 네이버 로그인을 직접 진행해주세요.")
            print("   - 아이디/비밀번호 입력")
            print("   - 캡차가 나타나면 해결")
            print("   - 2차 인증이 있으면 진행")
            print("💡 로그인이 완료되면 자동으로 다음 단계로 진행됩니다.")
            print("="*60 + "\n")
            
            # Wait for successful login by checking URL change
            max_wait_time = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                current_url = self.driver.current_url
                
                # Check if user has successfully logged in
                if "nid.naver.com" not in current_url:
                    # Additional verification - check for Naver main elements
                    try:
                        # Look for elements that indicate successful login
                        # This could be Naver's main page or any page that's not the login page
                        if "naver.com" in current_url and "nidlogin" not in current_url:
                            logger.info("Manual login detected - successful!", current_url=current_url)
                            print("✅ 로그인 성공이 확인되었습니다!")
                            return
                    except:
                        pass
                
                # Check every 2 seconds
                time.sleep(2)
                
                # Show progress dots
                elapsed = int(time.time() - start_time)
                if elapsed % 10 == 0:
                    remaining = max_wait_time - elapsed
                    print(f"⏳ 로그인 대기 중... (남은 시간: {remaining}초)")
            
            # Timeout
            raise Exception("로그인 대기 시간이 초과되었습니다. (5분)")
            
        except Exception as e:
            logger.error("Manual login failed", error=str(e))
            raise Exception(f"수동 로그인 실패: {str(e)}")
    
    def _navigate_to_blog_write(self):
        """Navigate to blog write page"""
        try:
            logger.info("Navigating to blog write page")
            print("📝 네이버 블로그 글쓰기 페이지로 이동 중...")
            
            self.driver.get("https://blog.naver.com/GoBlogWrite.naver")
            time.sleep(3)
            
            # Switch to main frame
            iframe = self.wait.until(EC.presence_of_element_located((By.ID, "mainFrame")))
            self.driver.switch_to.frame(iframe)
            
            logger.info("Navigated to blog write page successfully")
            print("✅ 블로그 글쓰기 페이지 이동 완료!")
            
        except Exception as e:
            logger.error("Failed to navigate to blog write page", error=str(e))
            raise Exception(f"블로그 글쓰기 페이지 이동 실패: {str(e)}")
    
    def _write_blog_content(self, title: str, content: str):
        """Write blog title and content"""
        try:
            logger.info("Writing blog content", title_length=len(title), content_length=len(content))
            print(f"✏️  블로그 제목 입력 중: '{title}'")
            
            # Title input
            title_input = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "se-input")))
            title_input.clear()
            
            # Type title character by character for visual effect
            for char in title:
                title_input.send_keys(char)
                time.sleep(0.05)  # Small delay for visual effect
            
            print("✅ 제목 입력 완료!")
            print(f"📄 블로그 내용 입력 중... ({len(content)}자)")
            
            # Content input
            content_area = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "se-content")))
            content_area.click()
            time.sleep(1)
            
            # Type content with visual feedback
            content_lines = content.split('\n')
            for i, line in enumerate(content_lines):
                content_area.send_keys(line)
                if i < len(content_lines) - 1:
                    content_area.send_keys('\n')
                
                # Show progress for long content
                if len(content_lines) > 10 and (i + 1) % 5 == 0:
                    progress = int((i + 1) / len(content_lines) * 100)
                    print(f"   진행률: {progress}% ({i + 1}/{len(content_lines)} 줄)")
                
                time.sleep(0.1)
            
            logger.info("Blog content written successfully")
            print("✅ 블로그 내용 입력 완료!")
            
        except Exception as e:
            logger.error("Failed to write blog content", error=str(e))
            raise Exception(f"블로그 글 작성 실패: {str(e)}")
    
    def _publish_blog(self):
        """Publish the blog post"""
        try:
            logger.info("Publishing blog post")
            print("🚀 블로그 발행 중...")
            
            # Find and click publish button
            publish_btn = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "publish_btn")))
            publish_btn.click()
            time.sleep(2)
            print("   발행 버튼 클릭 완료")
            
            # Handle any confirmation dialogs
            try:
                confirm_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '발행')]")
                confirm_btn.click()
                time.sleep(2)
                print("   확인 대화상자 처리 완료")
            except NoSuchElementException:
                print("   확인 대화상자 없음 - 바로 발행")
            
            logger.info("Blog post published successfully")
            print("🎉 블로그 발행 완료!")
            
        except Exception as e:
            logger.error("Failed to publish blog post", error=str(e))
            raise Exception(f"블로그 글 발행 실패: {str(e)}")
    
    def post_to_naver_blog(self, post_data: dict, naver_account: dict) -> dict:
        """
        Main method to post a blog entry to Naver blog with Puppeteer (preferred) or Selenium fallback
        """
        account_id = naver_account.get("id", "unknown")
        
        # Try Puppeteer first (more stable for cloud environments)
        if PUPPETEER_AVAILABLE:
            try:
                logger.info("Attempting blog posting with Puppeteer (preferred)", 
                           title=post_data.get("title"), 
                           naver_id=account_id,
                           session_id=self.session_id)
                
                result = post_blog_with_puppeteer(
                    naver_id=account_id,
                    task_id=self.session_id,
                    title=post_data["title"],
                    content=post_data["content"],
                    category=post_data.get("category"),
                    tags=post_data.get("tags"),
                    progress_callback=None  # Could add callback support later
                )
                
                logger.info("Blog posting completed successfully with Puppeteer", result=result)
                return result
                
            except Exception as puppeteer_error:
                logger.warning("Puppeteer failed, falling back to Selenium", 
                              error=str(puppeteer_error))
                # Continue to Selenium fallback below
        
        # Selenium fallback
        try:
            logger.info("Starting blog posting task with Selenium fallback", 
                       title=post_data.get("title"), 
                       naver_id=account_id,
                       session_id=self.session_id)
            
            # Clean up any leftover profiles first
            self._cleanup_all_temp_profiles()
            
            # Initialize driver with isolated profile
            self.driver = self._init_driver(account_id)
            self.wait = WebDriverWait(self.driver, 15)
            
            # Manual login (no credentials needed)
            self._wait_for_manual_login()
            
            # Navigate to blog write page
            self._navigate_to_blog_write()
            
            # Write content
            self._write_blog_content(post_data["title"], post_data["content"])
            
            # Publish blog
            self._publish_blog()
            
            result = {
                "success": True,
                "message": "네이버 블로그 포스팅이 성공적으로 완료되었습니다. (Selenium 사용)",
                "title": post_data["title"],
                "content_length": len(post_data["content"]),
                "posted_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": self.session_id,
                "automation_engine": "Selenium"
            }
            
            logger.info("Blog posting completed successfully with Selenium", result=result)
            return result
            
        except Exception as e:
            logger.error("Both Puppeteer and Selenium failed", 
                        puppeteer_available=PUPPETEER_AVAILABLE,
                        error=str(e), 
                        account_id=account_id, 
                        session_id=self.session_id)
            raise e
            
        finally:
            # Always cleanup browser and profile (Selenium only)
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                    logger.info("Chrome driver cleaned up")
                except Exception as cleanup_error:
                    logger.warning("Failed to cleanup driver", error=str(cleanup_error))
            
            # Clean up isolated profile directory
            self._cleanup_profile()