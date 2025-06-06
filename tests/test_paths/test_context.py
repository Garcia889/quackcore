# tests/test_paths/test_context.py
"""
Tests for project context models.
"""

from pathlib import Path

from quackcore.paths.context import ContentContext, ProjectContext, ProjectDirectory


class TestProjectDirectory:
    """Tests for the ProjectDirectory class."""

    def test_basic_directory(self) -> None:
        """Test creating a basic directory model."""
        dir_model = ProjectDirectory(
            name="src", path=Path("/project/src"), is_source=True
        )

        assert dir_model.name == "src"
        assert dir_model.path == Path("/project/src")
        assert dir_model.rel_path is None
        assert dir_model.is_source is True
        assert dir_model.is_output is False
        assert dir_model.is_data is False
        assert dir_model.is_config is False
        assert dir_model.is_test is False
        assert dir_model.is_asset is False
        assert dir_model.is_temp is False

        # Test string representation
        assert str(dir_model) == "/project/src"

    def test_full_directory(self) -> None:
        """Test creating a directory model with all attributes."""
        dir_model = ProjectDirectory(
            name="data",
            path=Path("/project/data"),
            rel_path=Path("data"),
            is_source=False,
            is_output=False,
            is_data=True,
            is_config=False,
            is_test=False,
            is_asset=False,
            is_temp=False,
        )

        assert dir_model.name == "data"
        assert dir_model.path == Path("/project/data")
        assert dir_model.rel_path == Path("data")
        assert dir_model.is_source is False
        assert dir_model.is_data is True


class TestProjectContext:
    """Tests for the ProjectContext class."""

    def test_basic_context(self) -> None:
        """Test creating a basic project context."""
        context = ProjectContext(root_dir=Path("/project"), name="test-project")

        assert context.root_dir == Path("/project")
        assert context.name == "test-project"
        assert context.directories == {}
        assert context.config_file is None

        # Test string representation
        assert "ProjectContext" in str(context)
        assert "/project" in str(context)

    def test_get_directories(self) -> None:
        """Test getting directories from the context."""
        context = ProjectContext(root_dir=Path("/project"))

        # Add directories
        src_dir = ProjectDirectory(
            name="src", path=Path("/project/src"), is_source=True
        )
        output_dir = ProjectDirectory(
            name="output", path=Path("/project/output"), is_output=True
        )
        data_dir = ProjectDirectory(
            name="data", path=Path("/project/data"), is_data=True
        )
        config_dir = ProjectDirectory(
            name="config", path=Path("/project/config"), is_config=True
        )

        context.directories = {
            "src": src_dir,
            "output": output_dir,
            "data": data_dir,
            "config": config_dir,
        }

        # Test getting directories by type
        assert context.get_source_dir() == Path("/project/src")
        assert context.get_output_dir() == Path("/project/output")
        assert context.get_data_dir() == Path("/project/data")
        assert context.get_config_dir() == Path("/project/config")

        # Test getting by name
        assert context.get_directory("src") == Path("/project/src")
        assert context.get_directory("output") == Path("/project/output")
        assert context.get_directory("nonexistent") is None

    def test_add_directory(self) -> None:
        """Test adding a directory to the context."""
        context = ProjectContext(root_dir=Path("/project"))

        # Add directory using the add_directory method
        context.add_directory(name="src", path=Path("/project/src"), is_source=True)

        # Verify the directory was added
        assert "src" in context.directories
        assert context.directories["src"].name == "src"
        assert context.directories["src"].path == Path("/project/src")
        assert context.directories["src"].is_source is True

        # Test adding with relative path calculation
        context.add_directory(
            name="output", path=Path("/project/output"), is_output=True
        )
        assert context.directories["output"].rel_path == Path("output")

        # Test adding path outside project root (rel_path should be None)
        context.add_directory(
            name="external",
            path=Path("/external/path"),
        )
        assert context.directories["external"].rel_path is None


class TestContentContext:
    """Tests for the ContentContext class."""

    def test_basic_content_context(self) -> None:
        """Test creating a basic content context."""
        context = ContentContext(
            root_dir=Path("/project"),
            content_type="tutorial",
            content_name="example",
            content_dir=Path("/project/src/tutorials/example"),
        )

        assert context.root_dir == Path("/project")
        assert context.content_type == "tutorial"
        assert context.content_name == "example"
        assert context.content_dir == Path("/project/src/tutorials/example")
        assert context.directories == {}

    def test_content_directories(self) -> None:
        """Test content context with directories."""
        context = ContentContext(root_dir=Path("/project"))

        # Add directories
        context.add_directory(
            name="assets", path=Path("/project/assets"), is_asset=True
        )
        context.add_directory(name="temp", path=Path("/project/temp"), is_temp=True)

        # Test getting content-specific directories
        assert context.get_assets_dir() == Path("/project/assets")
        assert context.get_temp_dir() == Path("/project/temp")

        # Test with missing directories
        context = ContentContext(root_dir=Path("/project"))
        assert context.get_assets_dir() is None
        assert context.get_temp_dir() is None

    def test_inherit_from_project_context(self) -> None:
        """Test inheriting from a project context."""
        project_context = ProjectContext(root_dir=Path("/project"), name="test-project")

        # Add directories to project context
        project_context.add_directory(
            name="src", path=Path("/project/src"), is_source=True
        )
        project_context.add_directory(
            name="assets", path=Path("/project/assets"), is_asset=True
        )

        # Create content context from project context
        content_context = ContentContext(
            root_dir=project_context.root_dir,
            directories=project_context.directories,
            config_file=project_context.config_file,
            name=project_context.name,
            content_type="tutorial",
        )

        # Verify inheritance
        assert content_context.root_dir == Path("/project")
        assert content_context.name == "test-project"
        assert "src" in content_context.directories
        assert "assets" in content_context.directories
        assert content_context.get_source_dir() == Path("/project/src")
        assert content_context.get_assets_dir() == Path("/project/assets")
        assert content_context.content_type == "tutorial"
