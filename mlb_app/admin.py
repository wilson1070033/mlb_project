from django.contrib import admin
from .models import Team, Player, GameLog, SearchHistory

class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'abbreviation', 'league', 'division', 'city')
    search_fields = ('name', 'abbreviation', 'city')
    list_filter = ('league', 'division')

class PlayerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mlb_id', 'current_team', 'primary_position', 'birth_date', 'bat_hand')
    search_fields = ('full_name', 'mlb_id')
    # Using current_team (which will use Team's __str__) for filtering.
    # If Team.__str__ is just the name, this is fine.
    # Otherwise, current_team__name might be preferred if available and indexed.
    list_filter = ('current_team', 'primary_position', 'bat_hand')

class GameLogAdmin(admin.ModelAdmin):
    list_display = ('player', 'game_date', 'opponent_team', 'at_bats', 'hits', 'runs', 'rbi', 'home_runs')
    # Using player__current_team for filtering.
    # If Team.__str__ is just the name, this is fine.
    # Otherwise, player__current_team__name might be preferred.
    list_filter = ('game_date', 'player__current_team')
    search_fields = ('player__full_name', 'opponent_team__name')

class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('search_query', 'search_type', 'search_time', 'results_count', 'ip_address')
    list_filter = ('search_type', 'search_time')
    search_fields = ('search_query', 'ip_address')

admin.site.register(Team, TeamAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(GameLog, GameLogAdmin)
admin.site.register(SearchHistory, SearchHistoryAdmin)
