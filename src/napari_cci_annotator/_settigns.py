import sys
from pathlib import Path

from qtpy.QtCore import QSettings
from qtpy.QtWidgets import QApplication, QFileDialog, QMessageBox


class Settings:
    def __init__(self, org_name: str = "cci.gu", app_name: str = "cci-annotator"):
        self.settings = QSettings(org_name, app_name)

    @property
    def model_path(self) -> Path | None:
        """Return stored model_path if it exists, otherwise prompt the user."""
        value = self.settings.value("model_path", type=str)
        if value and Path(value).exists():
            return Path(value)

        # If not found or invalid, open a folder selector

        QMessageBox.information(None, "Select Model Directory", "No ditectory for the annotation models is set. Press ok and select the directory where the models are stored.")
        
        #app = QApplication.instance() or QApplication(sys.argv)
        directory = QFileDialog.getExistingDirectory(
            None, "Select Model Directory", str(Path.home())
        )

        if directory:
            self.model_path = Path(directory)
            QMessageBox.information(
                None, "Model Path Saved", f"Saved model path:\n{directory}"
            )
            return Path(directory)
        else:
            QMessageBox.warning(None, "No Path Selected", "No model path selected.")
            return None

    @model_path.setter
    def model_path(self, path: str | Path):
        """Store a new model path persistently."""
        self.settings.setValue("model_path", str(path))
        
    def remove_model_path(self):
        """Remove the stored model_path setting."""
        self.settings.remove("model_path")
        QMessageBox.information(None, "Model Path Removed", "Model path has been cleared.")


# Example usage
# if __name__ == "__main__":
#     s = Settings("MyOrg", "MyApp")
#     model_dir = s.model_path
#     if model_dir:
#         print(f"Model path: {model_dir}")
#     else:
#         print("No model path set.")
