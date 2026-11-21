import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('clean_mac_tasks', Path(__file__).resolve().parents[1]/'tools/mac_tasks.py')
tasks=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tasks)

class SigningProfileTests(unittest.TestCase):
    def profile(self):
        container='iCloud.designs.struve.freetarget.sync'
        return {'Platform':['OSX'], 'ProvisionsAllDevices':True, 'Entitlements':{
            'com.apple.application-identifier':'PKH73HWP3S.designs.struve.freetarget.desktop.preview',
            'com.apple.developer.team-identifier':'PKH73HWP3S',
            'com.apple.developer.icloud-container-identifiers':[container],
            'com.apple.developer.ubiquity-container-identifiers':[container],
            'com.apple.developer.icloud-services':'*',
            'com.apple.developer.icloud-container-environment':'Production'}}
    def test_required_identifiers_come_from_profile(self):
        p=self.profile()
        e=tasks.icloud_entitlements(p,'designs.struve.freetarget.desktop.preview')
        for key in ('com.apple.application-identifier','com.apple.developer.team-identifier',
                    'com.apple.developer.icloud-container-environment'):
            self.assertEqual(e[key],p['Entitlements'][key])
    def test_wrong_app_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'bundle identifier'):
            tasks.icloud_entitlements(self.profile(),'wrong.app')
    def test_missing_shared_container_is_rejected(self):
        p=self.profile();p['Entitlements']['com.apple.developer.ubiquity-container-identifiers']=[]
        with self.assertRaisesRegex(ValueError,'shared iCloud container'):
            tasks.icloud_entitlements(p,'designs.struve.freetarget.desktop.preview')
