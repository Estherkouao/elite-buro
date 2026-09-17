from django.contrib import admin
from .models import OccupancySnapshot, ForecastLog


@admin.register(OccupancySnapshot)
class OccupancySnapshotAdmin(admin.ModelAdmin):
    list_display = ("workspace", "timestamp", "occupancy_count", "capacity", "occupancy_rate")
    list_filter = ("workspace", "space_type")
    date_hierarchy = "timestamp"
    autocomplete_fields = ["workspace"]


@admin.register(ForecastLog)
class ForecastLogAdmin(admin.ModelAdmin):
    list_display = ("workspace", "target_datetime", "occupancy_rate_predicted", "category_predicted", "created_at")
    list_filter = ("workspace", "category_predicted")
    date_hierarchy = "target_datetime"
    autocomplete_fields = ["workspace"]
