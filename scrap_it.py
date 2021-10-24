import os
import re
from time import sleep
from typing import List

import selenium
import xlsxwriter
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

#  constants
TRED_URL = 'https://www.tred.com/buy?body_style=&distance=50&exterior_color_id=&make=&miles_max=100000&miles_min=0&model=&page_size=24&price_max=100000&price_min=0&query=&requestingPage=buy&sort=desc&sort_field=updated&status=active&year_end=2022&year_start=1998&zip='
DRIVER_PATH = os.getenv(
    'DRIVER_PATH',
    os.getcwd() + '\\chromedriver\\chromedriver.exe'
)
WAIT_TIME = int(os.getenv('WAIT_TIME', '2'))


class Car():
    """Describes a car
    """

    def __init__(self, name: str, price: str, summary: str, options: str) \
            -> None:
        self.name = name
        self.price = price
        self.summary = summary
        self.options = options

        pass

    def __str__(self) -> str:
        return 'Name: {}, Price: {}'.format(self.name, self.price)


class CredSurfer():
    """This is a cred surfer class
    """

    # preferences
    _options = Options()
    _options.headless = True  # initiates a headless browser

    # disables image to load pages faster since image is not needed
    _options.add_experimental_option(
        "prefs",
        {"profile.managed_default_content_settings.images": 2}
    )

    _service = Service(DRIVER_PATH)  # path to chrome webdriver

    def __init__(self) -> None:

        # confirms browser set up is fine
        self._lunch_browser()
        self._close_browser()
        print('browser set up is fine')

        pass

    def _lunch_browser(self) -> bool:
        """Lunches browser and opens tred url
        """
        try:
            # lunch chrome as browser
            self.browser = Chrome(options=self._options, service=self._service)

            self.browser.get(TRED_URL)  # opens base url
            self._confirm_page_load()  # confirms page load
        except selenium.common.exceptions.WebDriverException:
            raise ConnectionError('Browser connectivity issue')

        return True

    def _close_browser(self) -> None:
        """Closes current browser section
        """

        self.browser.quit()

        pass

    def filter_by_location(
        self,
        radius: str = None,
        zip: int = None,
        limit: int = 999999999
    ) -> List[Car]:
        """Filters cars by radius and zip code, writes result to
        search_results.xlsx and returns list of cars

        Args:
            radius (str, optional): radius format(100 mi.). Defaults to None.
            zip (int, optional): zip code. Defaults to None.
            limit (int, optional): result limit. Defaults to 999999999.

        Returns:
            List[Car]: List of car object
        """
        # sets maximum limit if None
        limit = 999999999 if limit is None else limit
        self._validate_limit

        self._lunch_browser()  # lunches browser for current session

        # load browser with radius and zip
        if radius and zip:

            sleep(WAIT_TIME)  # delay to load page

            # selects the location tags
            radius_select = self.browser.find_element(
                By.XPATH,
                "//div[contains(@class, 'radius')]/select"
            )
            zip_input = self.browser.find_element(
                By.XPATH,
                "//div[contains(@class, 'zip')]/input"
            )

            # gets list of allowed selections for the radius select tag
            avail_radius = (radius_select.text).split('\n')
            print(avail_radius)
            # validates the inputs
            self._validate_radius(radius, avail_radius)
            self._validate_zip(zip)

            # assigns the user's input to get filtered results
            Select(radius_select).select_by_visible_text(radius)
            zip_input.send_keys(zip)

        sleep(WAIT_TIME)  # delay to load page

        # gets initial window height
        previous_height = self.browser.execute_script(
            "return document.body.scrollHeight"
        )

        # gets all anchor for result displayed
        search_result = self.browser.find_elements(
            By.XPATH,
            "//div[contains(@class, 'card') and \
                not(@class='card promotion')]/div/a"
        )

        while len(search_result) < limit:
            # Scroll down to bottom
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            sleep(WAIT_TIME)  # delay to load page

            # calculate current scroll height and compare with previous \
            # scroll height
            current_height = self.browser.execute_script(
                "return document.body.scrollHeight"
            )
            # gets all anchor for result displayed
            search_result = self.browser.find_elements(
                By.XPATH,
                "//div[contains(@class, 'card') and \
                    not(@class='card promotion')]/div/a"
            )

            if current_height == previous_height:
                break
            previous_height = current_height

        # retrieves the href(links) to cars
        search_anchors = [
            result.get_attribute('href') for result in search_result
        ]

        # extracts all the car details
        results = self._get_car_details(search_anchors, limit)

        self._writes_to_file(results)  # writes results

        self._close_browser()  # closes browser for session

        return results

    def _get_car_details(self, anchors_href: List[str], limit: int) \
            -> List[Car]:
        """Extract all required details by open the anchors href

        Args:
            anchors_href (List[str]): list href
            limit (int): page limit

        Returns:
            List[Car]: list of car objects
        """

        car_details = []  # result

        for count, link in enumerate(anchors_href):
            # ensures limit is not exceeded

            if count >= limit:
                break

            self.browser.get(link)  # opens car page
            self._confirm_page_load()  # confirms page load

            # extracts name by class
            raw_name = self.browser.find_element(By.CLASS_NAME, 'bigger')

            # uses regex to extract the name from the two formats available
            try:
                name = re.search(
                    "'s(.*)For Sale",
                    raw_name.text
                ).group(1).strip()

            except AttributeError:
                name = re.search(
                    "(.*)For Sale",
                    raw_name.text
                ).group(1).strip()

            # tries to get price tag, observed sold when unavailable
            try:
                price = self.browser.find_element(
                    By.XPATH, "//div[contains(@class, 'price-box')]/h2"
                ).text

            except selenium.common.exceptions.NoSuchElementException:
                price = 'Sold'

            # extracts all the vehicle summary
            table = self.browser.find_elements(By.ID, 'summary-table')
            table_rows = table[1].find_elements(By.XPATH, './/tbody/tr')

            summary_rows = []  # to store vehicle summary

            for row in table_rows:

                # skips title
                if row.text == 'Summary':
                    continue

                # extracts and formats the head and deatail
                row_head = row.find_element(By.XPATH, './/th').text
                row_detail = row.find_element(By.XPATH, './/td').text
                current_row = "'{}':'{}'".format(
                    row_head.strip().replace(':', ''),  # removes :
                    ''.join(row_detail.splitlines())  # reformats
                )
                summary_rows.append(current_row)

            summary = "[{}]".format(','.join(summary_rows))

            # extracts the vehicle options
            table = self.browser.find_elements(By.ID, 'options-table')

            options_rows = []  # to store vehicle options

            if table:
                table_rows = table[0].find_elements(By.XPATH, './/tbody/tr')
                start = False

                for row in table_rows:

                    # starts only when in options section
                    if row.text == 'Options':
                        start = True
                        continue

                    if start:
                        # extracts and format row details
                        row_detail = row.find_element(By.XPATH, './/td').text
                        current_row = "'{}'".format(
                            ''.join(row_detail.splitlines())  # reformats
                        )
                        options_rows.append(current_row)
            vehicle_options = "[{}]".format(','.join(options_rows))

            # creates car object
            current_car = Car(
                name=name, price=price,
                summary=summary,
                options=vehicle_options
            )
            car_details.append(current_car)

        return car_details

    def _writes_to_file(self, results: List[Car]) -> None:
        """Writes all car details to a .xlsx file

        Args:
            results (List[Car]): A list of car object
        """

        workbook = xlsxwriter.Workbook('search_results.xlsx')  # opens .xlsx
        sheet = workbook.add_worksheet()

        # writes header
        sheet.write("A1", "Names")
        sheet.write("B1", "Price")
        sheet.write("C1", 'Vehicle Summary')
        sheet.write("D1", 'Vehicle Options')

        # writes details
        for i, result in enumerate(results):
            sheet.write(i + 1, 0, result.name)
            sheet.write(i + 1, 1, result.price)
            sheet.write(i + 1, 2, result.summary)
            sheet.write(i + 1, 3, result.options)

        workbook.close()  # closes .xlsx

        pass

    def _validate_radius(self, radius: str, avail_radius: list) -> None:
        """Validates the radius input

        Args:
            radius (str): radius input
            avail_radius (list): [description]

        Raises:
            ValueError: Invalid radius, not an expected input
        """

        if radius not in avail_radius:
            self._close_browser()
            raise ValueError('Invalid radius')
        pass

    def _validate_zip(self, zip: int) -> None:
        """Validates the zip input

        Args:
            zip (int): zip input

        Raises:
            ValueError: Zip code must be of type int
        """

        if type(zip) is not int:
            self._close_browser()
            raise ValueError('Zip code must be of type int')
        pass

    def _validate_limit(self, limit: int) -> None:
        """Validates the limit input

        Args:
            limit (int): limit input

        Raises:
            ValueError: limit must be of type int
        """

        if type(limit) is not int:
            self._close_browser()
            raise ValueError('limit code must be of type int')
        pass

    def _confirm_page_load(self) -> None:
        """checks if page loaded
        """

        try:
            WebDriverWait(self.browser, WAIT_TIME).until(
                EC.presence_of_element_located((By.ID, 'main-logo'))
            )
        except selenium.common.exceptions.TimeoutException:
            self._close_browser()
            raise TimeoutError('Service is unavailable at the moment')
        except selenium.common.exceptions.WebDriverException:
            self._close_browser()
            raise ConnectionError('Browser connectivity issue')

        pass


def main():
    surf = CredSurfer()  # initiate CredSurfer

    # gets radius input
    radius = input("Enter your radius: ")

    # gets zip code input
    try:
        zip = int(input("Enter your zip code: "))
    except ValueError:
        zip = None

    # gets limit input
    try:
        limit = int(input("Enter your result limit: "))
    except ValueError:
        limit = None

    # filter cars by radius and zip
    surf.filter_by_location(radius=radius, zip=zip, limit=limit)


if __name__ == "__main__":
    main()
