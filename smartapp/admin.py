from django.contrib import admin
from .models import EMSLocality, EMSSensorData, EMSChannel, EMSData, EMSImage, EMSCallbackLog

@admin.register(EMSLocality)
class EMSLocalityAdmin(admin.ModelAdmin):
    list_display = ['site', 'loc_name', 'title', 'timezone', 'is_active', 'last_verified']
    list_filter = ['site', 'is_active', 'timezone']
    search_fields = ['loc_name', 'title', 'site']
    readonly_fields = ['last_callback_received']

@admin.register(EMSSensorData)
class EMSSensorDataAdmin(admin.ModelAdmin):
    list_display = ['locality', 'timestamp', 'temperature', 'humidity', 'pressure', 'wind_speed', 'rainfall']
    list_filter = ['locality', 'timestamp']
    search_fields = ['locality__loc_name', 'locality__title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'timestamp'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('locality')

@admin.register(EMSChannel)
class EMSChannelAdmin(admin.ModelAdmin):
    list_display = ['locality', 'channel_id', 'title', 'unit', 'is_active']
    list_filter = ['locality', 'is_active', 'range_group']
    search_fields = ['title', 'default_title']

@admin.register(EMSData)
class EMSDataAdmin(admin.ModelAdmin):
    list_display = ['channel', 'timestamp', 'value', 'interval', 'quality_score']
    list_filter = ['interval', 'is_validated', 'timestamp']
    search_fields = ['channel__title']
    date_hierarchy = 'timestamp'

@admin.register(EMSImage)
class EMSImageAdmin(admin.ModelAdmin):
    list_display = ['locality', 'channel', 'interval', 'culture', 'width', 'height', 'created_at']
    list_filter = ['interval', 'culture', 'created_at']
    search_fields = ['locality__loc_name', 'channel__title']

@admin.register(EMSCallbackLog)
class EMSCallbackLogAdmin(admin.ModelAdmin):
    list_display = ['callback_type', 'site', 'loc_name', 'success', 'created_at']
    list_filter = ['callback_type', 'success', 'created_at']
    search_fields = ['site', 'loc_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


