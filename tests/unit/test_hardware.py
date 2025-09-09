"""Unit tests for hardware optimization system."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from local_agents.hardware import HardwareOptimizer, HardwareProfile, hardware_optimizer


class TestHardwareProfile:
    """Test HardwareProfile dataclass."""

    def test_hardware_profile_creation(self):
        """Test HardwareProfile can be created with valid data."""
        profile = HardwareProfile(
            name="Test Profile",
            cpu_cores=8,
            memory_gb=16.0,
            recommended_models={"planning": "llama3.1:8b"},
            performance_settings={"max_concurrent_agents": 3},
            optimization_notes=["Test note"],
        )

        assert profile.name == "Test Profile"
        assert profile.cpu_cores == 8
        assert profile.memory_gb == 16.0
        assert profile.recommended_models == {"planning": "llama3.1:8b"}
        assert profile.performance_settings == {"max_concurrent_agents": 3}
        assert profile.optimization_notes == ["Test note"]


class TestHardwareOptimizer:
    """Test HardwareOptimizer class."""

    @pytest.fixture
    def optimizer(self):
        """Create a fresh HardwareOptimizer for testing."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Darwin",
                "cpu_count": 6,
                "memory_gb": 16.0,
                "architecture": "x86_64",
            }
            return HardwareOptimizer()

    def test_optimizer_initialization(self, optimizer):
        """Test HardwareOptimizer initializes correctly."""
        assert hasattr(optimizer, "detected_hardware")
        assert hasattr(optimizer, "profiles")

        # Test detected hardware structure
        hw = optimizer.detected_hardware
        assert "platform" in hw
        assert "cpu_count" in hw
        assert "memory_gb" in hw

        # Test profiles are loaded
        assert isinstance(optimizer.profiles, dict)
        assert len(optimizer.profiles) > 0

    def test_hardware_profiles_structure(self, optimizer):
        """Test that hardware profiles have correct structure."""
        profiles = optimizer.profiles

        # Test MacBook Pro profile exists
        assert "macbook_pro_intel_i7_16gb" in profiles

        for profile_name, profile in profiles.items():
            assert isinstance(profile, HardwareProfile)
            assert isinstance(profile.name, str)
            assert profile.cpu_cores > 0
            assert profile.memory_gb > 0
            assert isinstance(profile.recommended_models, dict)
            assert isinstance(profile.performance_settings, dict)
            assert isinstance(profile.optimization_notes, list)

    @patch("subprocess.run")
    def test_mac_model_detection(self, mock_subprocess):
        """Test macOS model detection from system_profiler."""
        # Mock successful system_profiler output
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Hardware:

    Hardware Overview:

      Model Name: MacBook Pro
      Model Identifier: MacBookPro16,1
      Processor Name: 6-Core Intel Core i7
      Processor Speed: 2.6 GHz
"""
        mock_subprocess.return_value = mock_result

        with patch(
            "local_agents.hardware.platform.system", return_value="Darwin"
        ):
            optimizer = HardwareOptimizer()
            assert "mac_model" in optimizer.detected_hardware
            assert "MacBook Pro" in optimizer.detected_hardware["mac_model"]

    @patch("subprocess.run")
    def test_mac_model_detection_failure(self, mock_subprocess):
        """Test macOS model detection handles failures gracefully."""
        # Mock failed system_profiler
        mock_subprocess.side_effect = FileNotFoundError()

        with patch(
            "local_agents.hardware.platform.system", return_value="Darwin"
        ):
            optimizer = HardwareOptimizer()
            assert optimizer.detected_hardware["mac_model"] == "Unknown Mac"

    def test_detect_macbook_pro_profile(self):
        """Test detection of MacBook Pro Intel i7 16GB profile."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Darwin",
                "cpu_count": 6,
                "memory_gb": 16.0,
                "mac_model": "MacBook Pro Intel Core i7",
            }

            optimizer = HardwareOptimizer()
            profile = optimizer.detect_best_profile()

            # Should detect MacBook Pro profile
            assert "MacBook Pro" in profile.name or "Custom" in profile.name
            assert profile.cpu_cores >= 6
            assert profile.memory_gb >= 15.5

    def test_detect_generic_high_end_profile(self):
        """Test detection of generic high-end profile."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Linux",
                "cpu_count": 16,
                "memory_gb": 32.0,
                "architecture": "x86_64",
            }

            optimizer = HardwareOptimizer()
            profile = optimizer.detect_best_profile()

            # Should detect high-end profile or create custom high-performance
            assert profile.cpu_cores >= 8
            assert profile.memory_gb >= 24

    def test_create_custom_profile_high_performance(self):
        """Test creation of custom high-performance profile."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Linux",
                "cpu_count": 8,
                "memory_gb": 20.0,
                "architecture": "x86_64",
            }

            optimizer = HardwareOptimizer()
            profile = optimizer._create_custom_profile()

            assert "High Performance" in profile.name
            assert profile.performance_settings["max_concurrent_agents"] >= 2
            assert profile.performance_settings["context_length"] >= 8192

    def test_create_custom_profile_medium_performance(self):
        """Test creation of custom medium-performance profile."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Linux",
                "cpu_count": 4,
                "memory_gb": 12.0,
                "architecture": "x86_64",
            }

            optimizer = HardwareOptimizer()
            profile = optimizer._create_custom_profile()

            assert "Medium Performance" in profile.name
            assert profile.performance_settings["max_concurrent_agents"] == 2
            assert profile.performance_settings["context_length"] == 8192

    def test_create_custom_profile_basic_performance(self):
        """Test creation of custom basic-performance profile."""
        with patch(
            "local_agents.hardware.HardwareOptimizer._detect_hardware"
        ) as mock_detect:
            mock_detect.return_value = {
                "platform": "Linux",
                "cpu_count": 2,
                "memory_gb": 4.0,
                "architecture": "x86_64",
            }

            optimizer = HardwareOptimizer()
            profile = optimizer._create_custom_profile()

            assert "Basic Performance" in profile.name
            assert profile.performance_settings["max_concurrent_agents"] == 1
            assert profile.performance_settings["context_length"] == 4096

    def test_get_optimization_config(self, optimizer):
        """Test getting optimization configuration."""
        profile = optimizer.detect_best_profile()
        config = optimizer.get_optimization_config(profile)

        assert isinstance(config, dict)
        assert "profile_name" in config
        assert "recommended_models" in config
        assert "performance_settings" in config
        assert "optimization_notes" in config
        assert "detected_hardware" in config

        assert config["profile_name"] == profile.name

    def test_get_optimization_config_default_profile(self, optimizer):
        """Test getting optimization config with default profile detection."""
        config = optimizer.get_optimization_config()

        assert isinstance(config, dict)
        assert "profile_name" in config
        # Should use detected profile when none specified

    def test_apply_optimization_success(self, optimizer):
        """Test successful application of optimization."""
        # Mock config manager
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = Mock()
        mock_config_manager.update_config_dict.return_value = (True, [])

        profile = optimizer.detect_best_profile()
        result = optimizer.apply_optimization(mock_config_manager, profile)

        assert result is True
        mock_config_manager.update_config_dict.assert_called_once()

    def test_apply_optimization_failure(self, optimizer):
        """Test failed application of optimization."""
        # Mock config manager with failure
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = Mock()
        mock_config_manager.update_config_dict.return_value = (
            False,
            ["Error message"],
        )

        profile = optimizer.detect_best_profile()
        result = optimizer.apply_optimization(mock_config_manager, profile)

        assert result is False

    def test_apply_optimization_exception(self, optimizer):
        """Test optimization application handles exceptions."""
        # Mock config manager that raises exception
        mock_config_manager = Mock()
        mock_config_manager.load_config.side_effect = Exception("Config error")

        profile = optimizer.detect_best_profile()
        result = optimizer.apply_optimization(mock_config_manager, profile)

        assert result is False

    def test_macbook_pro_profile_specific_settings(self, optimizer):
        """Test MacBook Pro profile has correct specific settings."""
        profile = optimizer.profiles["macbook_pro_intel_i7_16gb"]

        assert profile.name == "MacBook Pro Intel i7 16GB"
        assert profile.cpu_cores == 6
        assert profile.memory_gb == 16.0

        # Test performance settings
        settings = profile.performance_settings
        assert settings["max_concurrent_agents"] == 3
        assert settings["context_length"] == 16384
        assert settings["cache_size"] == 200
        assert settings["cache_ttl_seconds"] == 600

        # Test model recommendations exist
        models = profile.recommended_models
        assert "speed_optimized" in models
        assert "quality_optimized" in models
        assert "balanced" in models

        # Test specific model assignments
        speed_models = models["speed_optimized"]
        assert "planning" in speed_models
        assert "coding" in speed_models
        assert "testing" in speed_models
        assert "reviewing" in speed_models


class TestGlobalHardwareOptimizer:
    """Test the global hardware optimizer instance."""

    def test_global_hardware_optimizer_exists(self):
        """Test that global hardware optimizer instance exists."""
        assert hardware_optimizer is not None
        assert isinstance(hardware_optimizer, HardwareOptimizer)

    def test_global_optimizer_has_detected_hardware(self):
        """Test that global optimizer has detected hardware."""
        hw = hardware_optimizer.detected_hardware

        assert isinstance(hw, dict)
        assert "platform" in hw
        assert "cpu_count" in hw
        assert "memory_gb" in hw

        # Test values are reasonable for any system
        assert hw["cpu_count"] > 0
        assert hw["memory_gb"] > 0

    def test_global_optimizer_has_profiles(self):
        """Test that global optimizer has hardware profiles loaded."""
        profiles = hardware_optimizer.profiles

        assert isinstance(profiles, dict)
        assert len(profiles) > 0

        # Test that MacBook Pro profile exists
        assert "macbook_pro_intel_i7_16gb" in profiles
