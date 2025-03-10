# Infoslicer: A Sugar Activity for Creating and Editing Articles

This README provides documentation for Infoslicer, a Sugar activity built using Python and GTK.  It allows users to create and edit articles, potentially incorporating images and other media.  The project uses a custom book format stored in a zip file.

**1. Project Title and Short Description**

Infoslicer: A Sugar Activity for Article Creation and Editing

Infoslicer is a Sugar activity that enables users to create, edit, and manage articles.  It provides a simple interface for writing and organizing content.

[![License](https://img.shields.io/badge/License-GPLv2-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)


**2. Project Overview**

Infoslicer offers a dual-mode interface: a library view for browsing existing articles and an edit view for creating and modifying them.  Users can switch between these views using toolbar buttons. The application manages articles using a custom format stored in a zip file.  Images are handled through a custom image handling system.  The core functionality relies heavily on the Sugar framework's activity and widget components.

**Key Features:**

*   Article creation and editing
*   Library view for article browsing
*   Image handling and integration
*   Saving and loading articles from a zip file
*   Uses the Sugar framework for GUI

**Problem Solved:**

Provides a simple and intuitive way to create and manage articles within the Sugar learning environment.

**Use Cases:**

*   Students creating reports or stories
*   Teachers creating lesson materials
*   General purpose article writing and editing


**3. Table of Contents**

*   [Project Overview](#project-overview)
*   [Prerequisites](#prerequisites)
*   [Installation Guide](#installation-guide)
*   [Usage Examples](#usage-examples)
*   [Project Architecture](#project-architecture)
*   [Contributing Guidelines](#contributing-guidelines)


**4. Prerequisites**

*   **Sugar 3.0:** Infoslicer is designed specifically for the Sugar 3.0 environment.
*   **Python:**  The application is written in Python and requires a compatible interpreter.
*   **GTK 3.0:** The GUI is built using GTK 3.0.
*   **Necessary Python Libraries:**  `gi`, `gettext`, `uuid`, `json`, `shutil`, `zipfile`, `logging` and potentially others as indicated by `import` statements within the code.


**5. Installation Guide**

The installation process is not explicitly defined in the provided code.  Assuming the code is part of a Sugar activity, installation would involve deploying the application within the Sugar environment.  This typically involves packaging the code and resources into a suitable format for Sugar activities.  Details on this process are not provided within the given codebase.


**6. Configuration**

No explicit configuration files are apparent in the provided code.  The application's behavior might be influenced by environment variables or settings within the Sugar environment itself.

**7. Usage Examples**

The main activity class is `InfoslicerActivity`.  It uses a `Gtk.Notebook` to switch between the library and edit views.

```python
class InfoslicerActivity(activity.Activity):
    def __init__(self, handle):
        # ... initialization ...
        self.notebook = Gtk.Notebook() #Notebook to switch between views
        # ... more code ...
        self.notebook.append_page(self.library, None) #Library View
        self.notebook.append_page(self.edit, None)     #Edit View
        # ... more code ...
        self.__mode_button_clicked(search_button) #Starts in library view
```

The `__mode_button_clicked` function handles switching between the library and edit views:

```python
def __mode_button_clicked(self, button):
    if button.mode == 'search':
        self.edit_bar.unsensitize_all()
        self.notebook.set_current_page(0)  #Library
    else:
        self.edit_bar.sensitize_all()
        self.notebook.set_current_page(1)  #Edit
```

Article management is handled by the `book.py` file, which defines `WikiBook` and `CustomBook` classes.  The `CustomBook` class handles loading and saving from a zip file.  The specifics of article structure and data format are found within the `infoslicer.processing` module (not fully provided).

**8. Project Architecture**

The project uses a model-view-controller (MVC) like architecture.  The `book.py` file manages the data (model), while `library.py` and `edit.py` handle the presentation (view) and user interaction (controller). The `infoslicer.processing` module handles article parsing and data manipulation.

**9. Performance and Benchmarks**

No performance information or benchmarks are provided.

**10. API Reference**

Not applicable.  This is a Sugar activity, not a web service with an API.

**11. Contributing Guidelines**

Not explicitly defined.

**12. Testing**

No testing information is provided.


**13. Deployment**

Deployment would involve packaging the application as a Sugar activity.  Details are not provided.

**14. Security**

No specific security considerations are mentioned.

**15. Ethical Considerations**

Not applicable.

**16. Future Roadmap**

Not provided.

**17. License**

GPLv2

**18. Acknowledgments**

Not provided.

**19. Contact and Support**

Not provided.
