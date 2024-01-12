import asyncio
import os
from os.path import abspath
from inspect import getsourcefile
from pathlib import Path

import shutil
import urllib.request
import zipfile
import carb
import omni.ext
import omni.ui as ui
import omni.kit.asset_converter
import omni.usd
from pxr import Sdf
import warnings
import usdrt
import time


warnings.filterwarnings("ignore")
class IncarnateOmniverseExtension(omni.ext.IExt):
    def progress_callback(self, current_step: int, total: int):
        print(f"{current_step} of {total}")

    async def convert_asset_to_usd(self, input_asset: str, output_usd: str):
        converter_context = omni.kit.asset_converter.AssetConverterContext()
        # ... (other configurations)
        instance = omni.kit.asset_converter.get_instance()
        task = instance.create_converter_task(input_asset, output_usd, self.progress_callback, converter_context)
        success = await task.wait_until_finished()
        if not success:
            carb.log_error(task.get_status(), task.get_detailed_error())
        print("converting done")

    async def on_click_async(self, input_url):
        newfolder = os.path.join(self.download_path, input_url.model.get_value_as_string().split("/")[-1][:-4])
        os.makedirs(newfolder, exist_ok=True)

        self.destination_path = os.path.join(newfolder, input_url.model.get_value_as_string().split("/")[-1])

        with urllib.request.urlopen(input_url.model.get_value_as_string()) as response, open(self.destination_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file) 

        with zipfile.ZipFile(self.destination_path, 'r') as zip_ref:
            zip_ref.extractall(newfolder)

        await self.convert_asset_to_usd(os.path.join(newfolder,'obj', input_url.model.get_value_as_string().split("/")[-1][:-4] + ".obj"), os.path.join(newfolder, input_url.model.get_value_as_string().split("/")[-1][:-4] + ".usd"))
        object_id = input_url.model.get_value_as_string().split("/")[-1][:-4]

        asset_path = os.path.join(self.download_path, object_id, f'{object_id}.usd')

        omni.kit.commands.execute(
            'CreatePayloadCommand',
            usd_context=omni.usd.get_context(),
            path_to=Sdf.Path(f'/World/{object_id}'),  
            asset_path=asset_path,
            instanceable=False)
        self.objects.append(object_id)



    def on_startup(self, ext_id):
        print("[incarnate.omniverse] incarnate omniverse startup")
        self.objects = []

        self._count = 0
        cur_path = Path(abspath(getsourcefile(lambda:1)))
        self.currentdirectory = str(cur_path.parent.absolute())
        self.download_path = os.path.join(self.currentdirectory,"downloads")
        os.makedirs(self.download_path, exist_ok=True)
        self._window = ui.Window("Incarnate Avataar Extension", width=300, height=200)
        with self._window.frame:
            with ui.VStack():
                ui.Label("Enter mesh link from Avataar Creator")
                self.user_profile = os.path.expanduser("~")
                input_f = ui.StringField()          
                ui.Button("Import and View", clicked_fn=lambda: asyncio.ensure_future(self.on_click_async(input_f)))

    def on_shutdown(self):
        omni.kit.commands.execute(
            'DeletePrimsCommand',
            paths=[Sdf.Path(f'/World/{object_id}') for object_id in self.objects])
        objs = os.listdir(self.download_path)
        for obj in objs:
            try:
                shutil.rmtree(os.path.join(self.download_path,obj))
            except:
                print("Unable to delete")
        print("[incarnate.omniverse] incarnate omniverse shutdown")
