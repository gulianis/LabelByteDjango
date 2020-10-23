from django.test import TestCase
from .models import UserImageUpload, Upload, SquareLabel, PointLabel
from users.models import CustomUser
from django.urls import reverse
# Create your tests here.

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
#from selenium import webdriver
from selenium.webdriver.firefox.webdriver import WebDriver
"""
class StuffTestCase(TestCase):
    def test_stuff(self):
        self.assertEquals(1,2)

    def test_stuff_2(self):
        self.assertEquals(1,1)
"""
class ModelTest(TestCase):
    def test_ModelTest(self):
        # Test when zip file info is deleted from db all child nodes deleted
        CustomUser.objects.create(email="test100@gmail.com")
        user = CustomUser.objects.get(email="test100@gmail.com")
        Upload.objects.create(zipName="test", user=user)
        uploadObject = Upload.objects.get(zipName="test", user=user)
        UserImageUpload.objects.create(imageName="test", zipUpload=uploadObject)
        UserImageUploadObject = UserImageUpload.objects.get(imageName="test", zipUpload=uploadObject)
        SquareLabel.objects.create(image=UserImageUploadObject)
        SquareLabelObject = SquareLabel.objects.get(image=UserImageUploadObject)
        PointLabel.objects.create(image=UserImageUploadObject)
        PointLabelObject = PointLabel.objects.get(image=UserImageUploadObject)
        self.assertEquals(1, len(CustomUser.objects.all()))
        self.assertEquals(1, len(Upload.objects.all()))
        self.assertEquals(1, len(UserImageUpload.objects.all()))
        self.assertEquals(1, len(SquareLabel.objects.all()))
        self.assertEquals(1, len(PointLabel.objects.all()))
        uploadObject.delete()
        self.assertEquals(0, len(Upload.objects.all()))
        self.assertEquals(0, len(UserImageUpload.objects.all()))
        self.assertEquals(0, len(SquareLabel.objects.all()))
        self.assertEquals(0, len(PointLabel.objects.all()))

class WebsiteTest(TestCase):
    def test_not_logged_in(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('how-it-works'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
    def test_logged_in(self):
        test_user1 = CustomUser.objects.create_user(email='test10@gmail.com', password='1234cool')
        self.client.login(email="test10@gmail.com", password="1234cool")
        response = self.client.get(reverse('label'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        #response = self.client.get(reverse(''))



# class MySeleniumTests(StaticLiveServerTestCase):
#
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#         #cls.selenium = webdriver.Firefox(executable_path='/Users/sandeepguliani/Documents/geckodriver')
#         cls.selenium = WebDriver()
#         cls.selenium.implicitly_wait(10)
#
#     @classmethod
#     def tearDownClass(cls):
#         cls.selenium.implicitly_wait(10)
#         cls.selenium.quit()
#         super().tearDownClass()
#
#     def test_login(self):
#         test_user1 = CustomUser.objects.create_user(email='test10@gmail.com', password='1234cool')
#         self.selenium.get('%s%s' % (self.live_server_url, '/login/'))
#         username_input = self.selenium.find_element_by_name("username")
#         username_input.send_keys('test10@gmail.com')
#         password_input = self.selenium.find_element_by_name("password")
#         password_input.send_keys('1234cool')
#         #self.selenium.find_element_by_xpath("//button[@title='Login']").click()
#         button = self.selenium.find_element_by_name("login-button")
#         button.click()
#         #self.assertEquals(reverse('home'), driver.getCurrentUrl())