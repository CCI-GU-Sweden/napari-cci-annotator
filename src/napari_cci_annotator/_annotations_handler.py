from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from qtpy.QtCore import QSortFilterProxyModel, Qt
from qtpy.QtGui import QStandardItem, QStandardItemModel
from qtpy.QtWidgets import QApplication, QStyle

from .morphometrics import morpho_data_generator, unaxon_morpho_data_generator


class NumericSortProxyModel(QSortFilterProxyModel):
    def lessThan(self, left, right):
        left_data = self.sourceModel().data(left, Qt.UserRole + 1)
        right_data = self.sourceModel().data(right, Qt.UserRole + 1)

        try:
            return float(left_data) < float(right_data)  # Numeric comparison
        except (ValueError, TypeError):
            return super().lessThan(left, right)  # Fallback to string


class AnnotationsHandler:
    def __init__(self):
        self._ann_model = QStandardItemModel()
        self._proxy_model = NumericSortProxyModel()
        self._proxy_model.setSourceModel(self._ann_model)
        self.executor = ThreadPoolExecutor()
        # self.model().setColumnCount(8)
        self.set_headers()

    def model(self):
        return self._proxy_model

    def set_headers(self, morpho_type='myelin'):
        self._morpho_type = morpho_type
        if morpho_type == "unmyelinated":
            headers = [
                "Unaxon id",
                "X coord",
                "Y coord",
                "Area (px2)",
                "status",
            ]
        else:
            headers = [
                "Myelin id",
                "Axon id",
                "X coord",
                "Y coord",
                "Area (px2)",
                "# parts",
                "Axon area",
                "Axon calcu.",
                "status",
            ]

        self._ann_model.setColumnCount(len(headers))

        for column, header in enumerate(headers):
            self._ann_model.setHeaderData(
                column,
                Qt.Horizontal,
                header,
            )

    def clear_model(self, morpho_type="myelin"):
        self._ann_model.clear()
        self.set_headers(morpho_type)

    def count(self):
        return self._ann_model.rowCount()

    def add_unaxon_annotations_to_model(
            self,
            unaxon_label_image,
            data_image,
            napariViewer,


    ):
        future = self.executor.submit(
            self._add_unaxon_annotations,
            unaxon_label_image,
            data_image,
            napariViewer,


        )
        return future

    def add_annotations_to_model(
        self, myelin_label_image, axon_label_image, data_image, napariViewer
    ):
        future = self.executor.submit(
            self._add_annotations,
            myelin_label_image,
            axon_label_image,
            data_image,
            napariViewer,
        )
        return future

    def _add_annotations(
        self,
        myelin_label_image,
        axon_label_image,
        data_image,
        progress_update_cb=None,
    ):
        self.clear_model()

        style = QApplication.style()

        cnt = 0
        gen = morpho_data_generator(
            myelin_label_image, axon_label_image, data_image
        )
        tot_nr_labels = next(gen)
        for data in gen:
            if data.empty:
                continue
            items = []
            myelin_label = data.myelin_label[0]
            myelinLabelItem = QStandardItem(str(myelin_label))
            myelinLabelItem.setData(myelin_label)
            myelinLabelItem.setData(data, Qt.UserRole + 2)
            items.append(myelinLabelItem)

            axon_label = data["axon_label"][0] if data["status_ok"][0] else "-"
            axonLabelItem = QStandardItem(str(axon_label))
            axonLabelItem.setData(axon_label)
            items.append(axonLabelItem)

            x = data["center_x"][0]
            xItem = QStandardItem(str(x))
            xItem.setData(x)
            items.append(xItem)

            y = data["center_y"][0]
            yItem = QStandardItem(str(y))
            yItem.setData(y)
            items.append(yItem)

            area = data.myelin_area[0]
            areaItem = QStandardItem(str(area))
            areaItem.setData(area)
            items.append(areaItem)

            nit = data["nr_of_parts"][0]
            nrItems = QStandardItem(str(nit))
            nrItems.setData(nit)
            items.append(nrItems)

            aa = data["axon_area"][0]
            aaItems = QStandardItem(str(aa))
            aaItems.setData(aa)
            items.append(aaItems)

            ac = data["axon_calculation"][0]
            acItems = QStandardItem(str(ac))
            acItems.setData(ac)
            items.append(acItems)

            statusItem = QStandardItem("")

            if not data["status_ok"][0]:
                statusItem.setIcon(
                    style.standardIcon(QStyle.SP_MessageBoxWarning)
                )
                statusItem.setToolTip(data["error_msg"][0])

            items.append(statusItem)

            self._ann_model.appendRow(items)
            print(f"adding {cnt} to model, status: {data['status_ok'][0]}")
            cnt += 1

            if progress_update_cb:
                progress_update_cb(cnt, tot_nr_labels)

        self.set_headers()

    def _add_unaxon_annotations(
            self,
            unaxon_label_image,
            data_image,
            progress_update_cb=None,
    ):
        self.clear_model("unmyelinated")

        style = QApplication.style()

        gen = unaxon_morpho_data_generator(
            unaxon_label_image,
            data_image,
        )

        tot_nr_labels = next(gen)
        cnt = 0

        for data in gen:
            if data.empty:
                continue

            items = []

            label = data["unaxon_label"][0]

            label_item = QStandardItem(str(label))
            label_item.setData(label, Qt.UserRole + 1)

            label_item.setData(data, Qt.UserRole + 2)

            items.append(label_item)

            x = data["center_x"][0]
            x_item = QStandardItem(str(x))
            x_item.setData(x, Qt.UserRole + 1)
            items.append(x_item)

            y = data["center_y"][0]
            y_item = QStandardItem(str(y))
            y_item.setData(y, Qt.UserRole + 1)
            items.append(y_item)

            area = data["unaxon_area"][0]
            area_item = QStandardItem(str(area))
            area_item.setData(area, Qt.UserRole + 1)
            items.append(area_item)

            status_item = QStandardItem("")

            if not data["status_ok"][0]:
                status_item.setIcon(
                    style.standardIcon(QStyle.SP_MessageBoxWarning)
                )
                status_item.setToolTip(data["error_msg"][0])

            items.append(status_item)

            self._ann_model.appendRow(items)

            cnt += 1

            if progress_update_cb:
                progress_update_cb(cnt, tot_nr_labels)

        self.set_headers("unmyelinated")

    def get_label_for_row(self, row):
        idx = self._proxy_model.index(row, 0)
        return float(self._proxy_model.data(idx))

    def get_coordinates_for_row(self, row):
        if self._morpho_type == "unmyelinated":
            x_col, y_col = 1, 2
        else:
            x_col, y_col = 2, 3

        x_idx = self._proxy_model.index(row, x_col)
        y_idx = self._proxy_model.index(row, y_col)

        return (
            float(self._proxy_model.data(x_idx)),
            float(self._proxy_model.data(y_idx)),
        )
    
    def get_status_msg_for_row(self, row):
        idx = self._proxy_model.index(row, 6)
        return str(self._proxy_model.data(idx))

    def remove_row(self, row):
        return self._proxy_model.removeRow(row)

    def _convert_morphometrics_to_nm(self, table, pixel_size_nm):
        result = table.copy()

        area_columns = [
            "myelin_area",
            "myelin_hole_area",
            "myelin_filled_area",
            "axon_area",
            "unaxon_area",
        ]

        length_columns = [
            "myelin_axis_minor_length",
            "myelin_axis_major_length",
            "myelin_feret_diameter_max",
            "myelin_feret_max",
            "myelin_feret_min",
            "myelin_width",
            "myelin_q25",
            "myelin_q75",
            "myelin_width_min_feret_direction",
            "myelin_width_max_feret_direction",
            "axon_feret_max",
            "axon_feret_min",
            "unaxon_axis_minor_length",
            "unaxon_axis_major_length",
            "unaxon_feret_diameter_max",
            "unaxon_feret_max",
            "unaxon_feret_min",
        ]

        rename_columns = {}

        if pixel_size_nm == 1:
            for col in area_columns:
                if col in result.columns:
                    rename_columns[col] = f"{col}_px2"

            for col in length_columns:
                if col in result.columns:
                    rename_columns[col] = f"{col}_px"

            result.rename(columns=rename_columns, inplace=True)
            result["pixel_size_nm_per_px"] = 1

            return result

        for col in area_columns:
            if col in result.columns:
                result[col] = (
                        pd.to_numeric(result[col], errors="coerce")
                        * pixel_size_nm ** 2
                )
                rename_columns[col] = f"{col}_nm2"

        for col in length_columns:
            if col in result.columns:
                result[col] = (
                        pd.to_numeric(result[col], errors="coerce")
                        * pixel_size_nm
                )
                rename_columns[col] = f"{col}_nm"

        result.rename(columns=rename_columns, inplace=True)

        result["pixel_size_nm_per_px"] = pixel_size_nm

        return result

    def generate_xls_report(self, name, pixel_size_nm):
        future = self.executor.submit(
            self._generate_xls_report,
            name,
            pixel_size_nm,
        )
        return future

    def _generate_xls_report(self, name, pixel_size_nm):
        total_table = pd.DataFrame()

        for row in range(self._ann_model.rowCount()):
            item = self._ann_model.item(row, 0)

            if item is None:
                continue

            data = item.data(Qt.UserRole + 2)

            if data is None:
                continue

            total_table = pd.concat(
                [total_table, data],
                axis=0,
                ignore_index=True,
            )

        if total_table.empty:
            raise ValueError("No morphometrics available to export.")

        total_table = self._convert_morphometrics_to_nm(
            total_table,
            pixel_size_nm,
        )

        total_table.to_excel(
            name,
            index=False,
            engine="xlsxwriter",
        )

