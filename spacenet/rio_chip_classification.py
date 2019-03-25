import os

import rastervision as rv

from .data import (get_rio_training_scene_info, get_rio_val_scene_info)

AOI_URI = "s3://spacenet-dataset/AOI_1_Rio/srcData/buildingLabels/Rio_OUTLINE_Public_AOI.geojson"

class ChipClassificationExperiments(rv.ExperimentSet):
    """Chip classificaiton experiments on SpaceNet Rio data.
    Be sure you've run the data prep notebook before running this experiment.
    """
    def scene_maker(self, task):
        def f(x):
            (raster_uri, label_uri) = x
            id = os.path.splitext(os.path.basename(raster_uri))[0]
            label_source = rv.LabelSourceConfig.builder(rv.CHIP_CLASSIFICATION_GEOJSON) \
                                               .with_uri(label_uri) \
                                               .with_ioa_thresh(0.5) \
                                               .with_use_intersection_over_cell(False) \
                                               .with_pick_min_class_id(True) \
                                               .with_background_class_id(2) \
                                               .with_infer_cells(True) \
                                               .build()

            return rv.SceneConfig.builder() \
                                 .with_task(task) \
                                 .with_id(id) \
                                 .with_raster_source(raster_uri) \
                                 .with_label_source(label_source) \
                                 .with_aoi_uri(AOI_URI) \
                                 .build()
        return f


    def exp_rio_resnet50_200chip(self, root_uri):
        task = rv.TaskConfig.builder(rv.CHIP_CLASSIFICATION) \
                    .with_chip_size(200) \
                    .with_classes({
                        "building": (1, "red"),
                        "no_building": (2, "black")
                    }) \
                    .build()

        backend = rv.BackendConfig.builder(rv.KERAS_CLASSIFICATION) \
                                  .with_task(task) \
                                  .with_model_defaults(rv.RESNET50_IMAGENET) \
                                  .with_debug(True) \
                                  .with_batch_size(16) \
                                  .with_num_epochs(40) \
                                  .with_config({
                                      "trainer": {
                                          "options": {
                                              "saveBest": True,
                                              "lrSchedule": [
                                                  {
                                                      "epoch": 0,
                                                      "lr": 0.0005
                                                  },
                                                  {
                                                      "epoch": 15,
                                                      "lr": 0.0001
                                                  },
                                                  {
                                                      "epoch": 30,
                                                      "lr": 0.00001
                                                  }
                                              ]
                                          }
                                      }
                                  }, set_missing_keys=True) \
                                  .build()

        make_scene = self.scene_maker(task)

        train_scenes = list(map(make_scene, get_rio_training_scene_info()))
        val_scenes = list(map(make_scene, get_rio_val_scene_info()))

        dataset = rv.DatasetConfig.builder() \
                                  .with_train_scenes(train_scenes) \
                                  .with_validation_scenes(val_scenes) \
                                  .build()

        experiment = rv.ExperimentConfig.builder() \
                                        .with_id('spacenet-rio-chip-classification') \
                                        .with_root_uri(root_uri) \
                                        .with_task(task) \
                                        .with_backend(backend) \
                                        .with_dataset(dataset) \
                                        .build()

        return experiment

if __name__ == '__main__':
    rv.main()
