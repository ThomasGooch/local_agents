"""Hardware-specific optimizations for Local Agents."""

import platform
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class HardwareProfile:
    """Hardware profile with optimization settings."""
    
    name: str
    cpu_cores: int
    memory_gb: float
    recommended_models: Dict[str, str]
    performance_settings: Dict[str, Any]
    optimization_notes: List[str]


class HardwareOptimizer:
    """Hardware-specific optimization for Local Agents."""
    
    def __init__(self):
        self.detected_hardware = self._detect_hardware()
        self.profiles = self._initialize_profiles()
    
    def _detect_hardware(self) -> Dict[str, Any]:
        """Detect current hardware configuration."""
        import psutil
        
        hardware_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=False),
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "cpu_freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
        }
        
        # Detect macOS specific information
        if platform.system() == "Darwin":
            try:
                # Get Mac model information
                result = subprocess.run(
                    ["system_profiler", "SPHardwareDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    hardware_info["mac_model"] = self._parse_mac_model(result.stdout)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                hardware_info["mac_model"] = "Unknown Mac"
        
        return hardware_info
    
    def _parse_mac_model(self, system_profiler_output: str) -> str:
        """Parse Mac model from system_profiler output."""
        lines = system_profiler_output.split('\n')
        for line in lines:
            if "Model Name:" in line:
                return line.split("Model Name:")[-1].strip()
            elif "Model Identifier:" in line:
                return line.split("Model Identifier:")[-1].strip()
        return "Unknown Mac"
    
    def _initialize_profiles(self) -> Dict[str, HardwareProfile]:
        """Initialize hardware profiles with optimized settings."""
        return {
            "macbook_pro_intel_i7_16gb": HardwareProfile(
                name="MacBook Pro Intel i7 16GB",
                cpu_cores=6,
                memory_gb=16.0,
                recommended_models={
                    "speed_optimized": {
                        "planning": "llama3.1:8b",
                        "coding": "codellama:7b",
                        "testing": "deepseek-coder:6.7b", 
                        "reviewing": "llama3.1:8b"
                    },
                    "quality_optimized": {
                        "planning": "llama3.1:8b",
                        "coding": "codellama:13b-instruct",
                        "testing": "deepseek-coder:6.7b",
                        "reviewing": "llama3.1:70b-instruct-q4_0"
                    },
                    "balanced": {
                        "planning": "llama3.1:8b", 
                        "coding": "codellama:7b-instruct",
                        "testing": "deepseek-coder:6.7b",
                        "reviewing": "llama3.1:8b"
                    }
                },
                performance_settings={
                    "max_concurrent_agents": 3,
                    "context_length": 16384,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enable_response_cache": True,
                    "cache_size": 200,
                    "cache_ttl_seconds": 600,
                    "enable_parallel_workflows": True,
                    "memory_cleanup_interval": 300,
                    "performance_monitoring": True
                },
                optimization_notes=[
                    "Optimized for MacBook Pro Intel i7 with 16GB RAM",
                    "Utilizes 6-core CPU with up to 3 concurrent agents",
                    "Large cache size takes advantage of 16GB memory",
                    "Extended cache TTL (10 minutes) for better hit rates",
                    "Parallel workflow execution enabled for performance"
                ]
            ),
            "macbook_air_m1_8gb": HardwareProfile(
                name="MacBook Air M1 8GB", 
                cpu_cores=8,
                memory_gb=8.0,
                recommended_models={
                    "speed_optimized": {
                        "planning": "llama3.1:8b",
                        "coding": "codellama:7b",
                        "testing": "phi:3.5",
                        "reviewing": "llama3.1:8b"
                    },
                    "quality_optimized": {
                        "planning": "llama3.1:8b",
                        "coding": "codellama:7b-instruct", 
                        "testing": "deepseek-coder:6.7b",
                        "reviewing": "llama3.1:8b"
                    }
                },
                performance_settings={
                    "max_concurrent_agents": 2,
                    "context_length": 8192,
                    "temperature": 0.7,
                    "max_tokens": 4096,
                    "enable_response_cache": True,
                    "cache_size": 100,
                    "cache_ttl_seconds": 300,
                    "enable_parallel_workflows": True,
                    "memory_cleanup_interval": 180,
                    "performance_monitoring": False
                },
                optimization_notes=[
                    "Optimized for MacBook Air M1 with 8GB unified memory",
                    "Limited to 2 concurrent agents due to memory constraints",
                    "Smaller cache size to preserve memory",
                    "More frequent memory cleanup (3 minutes)"
                ]
            ),
            "generic_high_end": HardwareProfile(
                name="High-End Desktop/Workstation",
                cpu_cores=8,
                memory_gb=32.0,
                recommended_models={
                    "speed_optimized": {
                        "planning": "llama3.1:8b",
                        "coding": "codellama:13b-instruct",
                        "testing": "deepseek-coder:6.7b",
                        "reviewing": "llama3.1:8b"
                    },
                    "quality_optimized": {
                        "planning": "llama3.1:70b-instruct-q4_0",
                        "coding": "codellama:34b-instruct-q4_0",
                        "testing": "deepseek-coder:33b-instruct-q4_0",
                        "reviewing": "llama3.1:70b-instruct-q4_0"
                    }
                },
                performance_settings={
                    "max_concurrent_agents": 4,
                    "context_length": 32768,
                    "temperature": 0.7,
                    "max_tokens": 8192,
                    "enable_response_cache": True,
                    "cache_size": 500,
                    "cache_ttl_seconds": 900,
                    "enable_parallel_workflows": True,
                    "memory_cleanup_interval": 600,
                    "performance_monitoring": True
                },
                optimization_notes=[
                    "High-end configuration for maximum performance",
                    "Can run large models and many concurrent agents",
                    "Extended context lengths and large cache",
                    "Long cache TTL (15 minutes) and cleanup intervals"
                ]
            )
        }
    
    def detect_best_profile(self) -> HardwareProfile:
        """Detect the best hardware profile for the current system."""
        memory_gb = self.detected_hardware["memory_gb"]
        cpu_cores = self.detected_hardware["cpu_count"]
        platform_name = self.detected_hardware["platform"]
        
        # MacBook Pro Intel i7 16GB detection
        if (platform_name == "Darwin" and 
            memory_gb >= 15.5 and memory_gb <= 16.5 and  # Allow some variance
            cpu_cores == 6):
            mac_model = self.detected_hardware.get("mac_model", "").lower()
            if "macbook pro" in mac_model and ("i7" in mac_model or "intel" in mac_model):
                return self.profiles["macbook_pro_intel_i7_16gb"]
        
        # MacBook Air M1 8GB detection
        if (platform_name == "Darwin" and
            memory_gb >= 7.5 and memory_gb <= 8.5 and
            cpu_cores == 8):
            mac_model = self.detected_hardware.get("mac_model", "").lower()
            if "macbook air" in mac_model and "m1" in mac_model:
                return self.profiles["macbook_air_m1_8gb"]
        
        # High-end system detection
        if memory_gb >= 24 and cpu_cores >= 8:
            return self.profiles["generic_high_end"]
        
        # Fallback: create custom profile based on detected hardware
        return self._create_custom_profile()
    
    def _create_custom_profile(self) -> HardwareProfile:
        """Create a custom hardware profile for unrecognized systems."""
        memory_gb = self.detected_hardware["memory_gb"]
        cpu_cores = self.detected_hardware["cpu_count"]
        
        # Determine performance tier
        if memory_gb >= 16 and cpu_cores >= 6:
            tier = "high"
            max_agents = min(cpu_cores // 2, 4)
            context_len = 16384
            cache_size = 200
        elif memory_gb >= 8 and cpu_cores >= 4:
            tier = "medium"
            max_agents = 2
            context_len = 8192
            cache_size = 100
        else:
            tier = "basic"
            max_agents = 1
            context_len = 4096
            cache_size = 50
        
        return HardwareProfile(
            name=f"Custom {tier.title()} Performance ({memory_gb}GB RAM, {cpu_cores} cores)",
            cpu_cores=cpu_cores,
            memory_gb=memory_gb,
            recommended_models={
                "balanced": {
                    "planning": "llama3.1:8b",
                    "coding": "codellama:7b" if tier != "basic" else "phi:3.5",
                    "testing": "deepseek-coder:6.7b" if tier != "basic" else "phi:3.5",
                    "reviewing": "llama3.1:8b"
                }
            },
            performance_settings={
                "max_concurrent_agents": max_agents,
                "context_length": context_len,
                "temperature": 0.7,
                "max_tokens": 4096,
                "enable_response_cache": True,
                "cache_size": cache_size,
                "cache_ttl_seconds": 300,
                "enable_parallel_workflows": tier != "basic",
                "memory_cleanup_interval": 300,
                "performance_monitoring": tier == "high"
            },
            optimization_notes=[
                f"Custom profile for {memory_gb}GB RAM, {cpu_cores} CPU cores",
                f"Performance tier: {tier}",
                f"Concurrent agents: {max_agents}",
                "Settings automatically adjusted based on detected hardware"
            ]
        )
    
    def get_optimization_config(self, profile: Optional[HardwareProfile] = None) -> Dict[str, Any]:
        """Get optimization configuration for the specified or detected profile."""
        if profile is None:
            profile = self.detect_best_profile()
        
        return {
            "profile_name": profile.name,
            "recommended_models": profile.recommended_models,
            "performance_settings": profile.performance_settings,
            "optimization_notes": profile.optimization_notes,
            "detected_hardware": self.detected_hardware
        }
    
    def apply_optimization(self, config_manager, profile: Optional[HardwareProfile] = None) -> bool:
        """Apply hardware optimization to configuration."""
        if profile is None:
            profile = self.detect_best_profile()
        
        try:
            # Get current config
            current_config = config_manager.load_config()
            
            # Apply performance settings
            updates = {}
            for key, value in profile.performance_settings.items():
                if key.startswith("max_concurrent_agents"):
                    updates["performance.max_concurrent_agents"] = value
                elif key.startswith("enable_response_cache"):
                    updates["performance.enable_response_cache"] = value
                elif key.startswith("cache_size"):
                    updates["performance.cache_size"] = value
                elif key.startswith("cache_ttl_seconds"):
                    updates["performance.cache_ttl_seconds"] = value
                elif key.startswith("enable_parallel_workflows"):
                    updates["performance.enable_parallel_workflows"] = value
                elif key.startswith("memory_cleanup_interval"):
                    updates["performance.memory_cleanup_interval"] = value
                elif key.startswith("performance_monitoring"):
                    updates["performance.performance_monitoring"] = value
                elif key == "context_length":
                    updates["context_length"] = value
                elif key == "temperature":
                    updates["temperature"] = value
                elif key == "max_tokens":
                    updates["max_tokens"] = value
            
            # Apply recommended models (use balanced profile if available)
            models = profile.recommended_models.get("balanced", 
                     profile.recommended_models.get("speed_optimized",
                     next(iter(profile.recommended_models.values()))))
            
            if "planning" in models:
                updates["agents.planning"] = models["planning"]
            if "coding" in models:
                updates["agents.coding"] = models["coding"]
            if "testing" in models:
                updates["agents.testing"] = models["testing"]
            if "reviewing" in models:
                updates["agents.reviewing"] = models["reviewing"]
            
            # Update configuration
            success, errors = config_manager.update_config_dict(updates)
            
            if success:
                console.print(f"[green]✓ Applied {profile.name} optimization[/green]")
                return True
            else:
                console.print("[red]✗ Failed to apply optimization:[/red]")
                for error in errors:
                    console.print(f"  [red]• {error}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Error applying optimization: {e}[/red]")
            return False
    
    def display_hardware_info(self) -> None:
        """Display detected hardware information."""
        hw = self.detected_hardware
        
        # Hardware info table
        hw_table = Table(title="Detected Hardware")
        hw_table.add_column("Component", style="cyan")
        hw_table.add_column("Value", style="green")
        
        hw_table.add_row("Platform", hw["platform"])
        hw_table.add_row("Architecture", hw["architecture"])
        hw_table.add_row("CPU Cores (Physical)", str(hw["cpu_count"]))
        hw_table.add_row("CPU Cores (Logical)", str(hw["cpu_count_logical"]))
        hw_table.add_row("Memory (GB)", f"{hw['memory_gb']:.1f}")
        
        if hw["cpu_freq_mhz"]:
            hw_table.add_row("CPU Frequency (MHz)", f"{hw['cpu_freq_mhz']:.0f}")
        
        if "mac_model" in hw:
            hw_table.add_row("Mac Model", hw["mac_model"])
        
        console.print(hw_table)
        
        # Detected profile
        profile = self.detect_best_profile()
        console.print(f"\n[bold blue]Recommended Profile:[/bold blue] {profile.name}")
        
        # Optimization notes
        notes_text = "\n".join(f"• {note}" for note in profile.optimization_notes)
        console.print(Panel(notes_text, title="Optimization Notes", border_style="blue"))
    
    def display_all_profiles(self) -> None:
        """Display all available hardware profiles."""
        for profile_key, profile in self.profiles.items():
            console.print(f"\n[bold cyan]{profile.name}[/bold cyan]")
            
            # Performance settings table
            settings_table = Table(title="Performance Settings")
            settings_table.add_column("Setting", style="yellow")
            settings_table.add_column("Value", style="green")
            
            for key, value in profile.performance_settings.items():
                settings_table.add_row(key.replace("_", " ").title(), str(value))
            
            console.print(settings_table)
            
            # Models table
            for model_type, models in profile.recommended_models.items():
                models_table = Table(title=f"{model_type.replace('_', ' ').title()} Models")
                models_table.add_column("Agent", style="magenta")
                models_table.add_column("Model", style="cyan")
                
                for agent, model in models.items():
                    models_table.add_row(agent.title(), model)
                
                console.print(models_table)


# Global hardware optimizer instance
hardware_optimizer = HardwareOptimizer()