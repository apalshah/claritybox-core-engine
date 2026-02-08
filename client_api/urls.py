from django.urls import path

from . import auth_views, views

urlpatterns = [
    # Auth
    path('auth/signup/', auth_views.signup, name='claritybox-signup'),
    path('auth/login/', auth_views.login, name='claritybox-login'),
    path('auth/refresh/', auth_views.refresh_token, name='claritybox-refresh'),
    path('auth/profile/', auth_views.profile, name='claritybox-profile'),

    # Market data
    path('market-metadata/', views.market_metadata, name='claritybox-market-metadata'),
    path('global-market-summary/', views.global_market_summary_v2, name='claritybox-global-market-summary'),
    path('chart/<str:market_type>/<str:symbol_name>/', views.chart_data, name='claritybox-chart-data'),
    path('momentum-alerts/', views.momentum_alerts, name='claritybox-momentum-alerts'),

    # Simulation
    path('simulate/', views.simulate, name='claritybox-simulate'),
    path('simulate/portfolio/', views.simulate_portfolio, name='claritybox-simulate-portfolio'),
    path('simulate/portfolio/advanced/', views.simulate_portfolio_advanced, name='claritybox-simulate-portfolio-advanced'),
]
