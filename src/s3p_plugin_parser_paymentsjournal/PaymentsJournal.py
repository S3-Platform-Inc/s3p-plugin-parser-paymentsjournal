import datetime
import time

from s3p_sdk.plugin.payloads.parsers import S3PParserBase
from s3p_sdk.types import S3PRefer, S3PDocument, S3PPlugin
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import dateparser


class PaymentsJournal(S3PParserBase):
    """
    A Parser payload that uses S3P Parser base class.
    """
    HOST = "https://www.paymentsjournal.com/news/"

    def __init__(self, refer: S3PRefer, plugin: S3PPlugin, web_driver: WebDriver, max_count_documents: int = None,
                 last_document: S3PDocument = None, num_scrolls: int = 5):
        super().__init__(refer, plugin, max_count_documents, last_document)

        # Тут должны быть инициализированы свойства, характерные для этого парсера. Например: WebDriver
        self._driver = web_driver
        self._wait = WebDriverWait(self._driver, timeout=20)
        self.num_scrolls = num_scrolls

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -

        self._driver.get(self.HOST)  # Открыть первую страницу с материалами в браузере
        time.sleep(3)

        # Cookies
        try:
            cookies_btn = self._driver.find_element(By.ID, 'normal-slidedown').find_element(By.XPATH,
                                                                                            '//*[@id="onesignal-slidedown-allow-button"]')
            self._driver.execute_script('arguments[0].click()', cookies_btn)
            self.logger.debug('Cookies убран')
        except:
            self.logger.debug('Не найден cookies')
            pass

        self.logger.debug('Прекращен поиск Cookies')
        time.sleep(3)

        flag = True
        while flag:
            self._driver.execute_script("window.scrollBy(0,document.body.scrollHeight)")
            self.logger.debug('Загрузка списка элементов...')

            counter = 0

            try:

                doc_table = self._driver.find_elements(By.TAG_NAME, 'article')
                last_doc_table_len = len(doc_table)

                while True:
                    # Scroll down to bottom
                    self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    counter += 1
                    # self.logger.info(f"counter = {counter}")

                    # Wait to load page
                    time.sleep(1)

                    try:
                        self._driver.execute_script('arguments[0].click()', self._driver.find_element(By.XPATH,
                                                                                                      '//*[contains(@class,\'dialog-close-button\')]'))
                    except:
                        self.logger.debug('Не найдена реклама')

                    # Wait to load page
                    time.sleep(1)

                    self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                    # Wait to load page
                    time.sleep(1)

                    doc_table = self._driver.find_elements(By.TAG_NAME, 'article')
                    new_doc_table_len = len(doc_table)
                    if last_doc_table_len == new_doc_table_len:
                        break
                    if counter > self.num_scrolls:
                        flag = False
                        break

                    try:
                        reg_btn = self._driver.find_element(By.CLASS_NAME, 'dialog-widget-content').find_element(
                            By.XPATH,
                            '//*[@id="elementor-popup-modal-433761"]/div/a')
                        reg_btn.click()
                        # self.logger.debug('Окно регистрации убрано')
                    except:
                        # self.logger.exception('Не найдено окно регистрации')
                        pass

                    # self.logger.debug('Прекращен поиск окна регистрации')
                    time.sleep(3)

            except Exception as e:
                self.logger.debug('Не удалось найти scroll')
                break

            self.logger.debug(f'Обработка списка элементов ({len(doc_table)})...')

            # Цикл по всем строкам таблицы элементов на текущей странице
            for element in doc_table:

                element_locked = False

                try:
                    title = element.find_element(By.CLASS_NAME, 'jeg_post_title').text
                    # title = element.find_element(By.XPATH, '//*[@id="feed-item-title-1"]/a').text

                except:
                    self.logger.exception('Не удалось извлечь title')
                    continue

                try:
                    web_link = element.find_element(By.CLASS_NAME, 'jeg_post_title').find_element(By.TAG_NAME,
                                                                                                  'a').get_attribute(
                        'href')
                except:
                    self.logger.exception('Не удалось извлечь web_link')
                    web_link = None

                try:
                    other_data = {
                        'author': element.find_element(By.CLASS_NAME, "jeg_meta_author").find_element(By.TAG_NAME,
                                                                                                      'a').text}
                except:
                    self.logger.debug('Не удалось извлечь other_data')
                    other_data = {}

                self._driver.execute_script("window.open('');")
                self._driver.switch_to.window(self._driver.window_handles[1])

                self._driver.get(web_link)
                self._wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, '.jeg_post_title')))

                try:
                    pub_date = dateparser.parse(self._driver.find_element(By.CLASS_NAME, 'jeg_meta_date').text)
                except:
                    self.logger.exception('Не удалось извлечь date')
                    continue

                try:
                    text_content = self._driver.find_element(By.CLASS_NAME, 'content-inner ').text
                except:
                    self.logger.debug('Не удалось извлечь text')
                    continue

                abstract = ''

                doc = S3PDocument(None,
                                  title,
                                  abstract,
                                  text_content,
                                  web_link,
                                  None,
                                  other_data,
                                  pub_date,
                                  datetime.datetime.now())

                self._find(doc)

                self._driver.close()
                self._driver.switch_to.window(self._driver.window_handles[0])

        # ---
        # ========================================
