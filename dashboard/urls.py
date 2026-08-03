from django.urls import path
from . import trainer_views
from . import views
from .views import TrainerDetailView
from .views import send_devis_email

from .views import (
    AdminIndexView,
    AdminUsersView,
    AdminUserCreateView,
    AdminUserUpdateView,
    AdminUserDeactivateView,
    AdminUserReactivateView,
    AdminUserDeleteView,
    AdminCompanyView,
    AdminCompanyCreateView,
    AdminCompanyUpdateView,
    AdminCompanyDeleteView,
    AdminCoworkingView,
    AdminCoworkingCategoryCreateView,
    AdminCoworkingCategoryEditView,
    AdminCoworkingCategoryDeleteView,
    AdminCoworkingEquipmentCreateView,
    AdminCoworkingEquipmentEditView,
    AdminCoworkingEquipmentDeleteView,
    AdminCoworkingWorkspaceCreateView,
    AdminCoworkingWorkspaceEditView,
    AdminCoworkingWorkspaceDeleteView,
    AdminCoworkingWorkspaceImageAddView,
    AdminCoworkingWorkspaceImageDeleteView,
    AdminCoworkingSpaceCreateView,
    AdminCoworkingSpaceEditView,
    AdminCoworkingSpaceDeleteView,
    AdminReservationsView,
    AdminReservationDetailView,
    AdminReservationEditView,
    AdminReservationCancelView,
    AdminReservationConfirmView,
    AdminReservationRefuseView,
    AdminFormationsView,
    AdminDomiciliationView,
    AdminDomiciliationRequestsListView,
    AdminDomiciliationRequestEditView,
    AdminDomiciliationRequestValidateView,
    AdminDomiciliationRequestRefuseView,
    AdminDomiciliationPlansListView,
    AdminDomiciliationPlanCreateView,
    AdminDomiciliationPlanEditView,
    AdminDomiciliationPlanDeleteView,
    AdminProfileView,
    AdminProfileEditView,
    AdminTestimonialListView,
    AdminTestimonialApproveView,
    AdminTestimonialRejectView,
    # Messages de contact
    AdminContactMessagesListView,
    AdminContactMessageDetailView,
    AdminContactMessageMarkReadView,
    AdminContactMessageMarkUnreadView,
    AdminContactMessageDeleteView,
    AdminDevisFormationListView,
    AdminDevisMarkReadView,
    AdminDevisMarkUnreadView,
    # Conciergerie
    AdminConciergerieListView,
    AdminConciergerieDetailView,
    AdminConciergerieValidateView,
    AdminConciergerieRefuseView,
)

from .member_dashboard import MemberDashboardView
from .views_extra import MemberPaymentsView







from .formation_admin import (
    AdminFormationDashboardView,
    AdminFormationsListView,
    AdminFormationCreateView,
    AdminFormationEditView,
    AdminFormationDeleteView,
    AdminFormationCategoryListView,
    AdminFormationCategoryCreateView,
    AdminFormationCategoryEditView,
    AdminFormationCategoryDeleteView,
    AdminSessionsListView,
    AdminSessionCreateView,
    AdminSessionEditView,
    AdminSessionDeleteView,
    AdminTrainersListView,
    AdminTrainersCreateView,
    AdminTrainersEditView,
    AdminTrainersDeleteView,
    FormationDetailView,
)

from .formation_inscriptions_admin import (
    AdminInscriptionsListView,
    AdminInscriptionValidateView,
    AdminInscriptionRefuseView,
    AdminInscriptionCancelView,
)




from .admin_payments import (

    AdminInvoicesDownloadView,
    AdminPaymentCancelView,
    AdminPaymentConfirmView,
    AdminPaymentMethodCreateView,
    AdminPaymentMethodDeleteView,
    AdminPaymentMethodEditView,
    AdminPaymentMethodListView,
    AdminPaymentRefundView,
    AdminPaymentsListView,
    AdminPaymentsReservationView,
    AdminReceiptDownloadView,
)


from .trainer_views import (
    TrainerDashboardView,
    TrainerSessionsView,
    TrainerSessionCreateView,
    TrainerSessionEditView,
    TrainerSessionDeleteView,
    TrainerStudentsView,
    TrainerRevenueView,
    TrainerFormationsView,
    TrainerDocumentsView,
    TrainerReviewsView,
    TrainerSettingsView,
    TrainerStudentDetailView,
    TrainerStudentValidateView,
    TrainerStudentRefuseView,
    TrainerFormationDetailView,
    delete_document,
    TrainerReservationsView,
    TrainerReservationDetailView,
    TrainerReservationCancelView,
    TrainerReservationCreateView,
    TrainerDevisFormationView,
)
from formation.views import DevisFormationDetailView



app_name = "dashboard_admin"

urlpatterns = [
    path("member-dashboard/", MemberDashboardView.as_view(), name="member_dashboard"),
    path("member-invoices/", MemberPaymentsView.as_view(), name="member_invoices"),

    path("", AdminIndexView.as_view(), name="index"),

    # Utilisateurs (CRUD)
    path("users/", AdminUsersView.as_view(), name="users"),
    path("users/create/", AdminUserCreateView.as_view(), name="user_create"),
    path("users/<uuid:user_id>/edit/", AdminUserUpdateView.as_view(), name="user_edit"),
    path(
        "users/<uuid:user_id>/deactivate/",
        AdminUserDeactivateView.as_view(),
        name="user_deactivate",
    ),
    path(
        "users/<uuid:user_id>/reactivate/",
        AdminUserReactivateView.as_view(),
        name="user_reactivate",
    ),
    path("users/<uuid:user_id>/delete/", AdminUserDeleteView.as_view(), name="user_delete"),

    # Entreprises (CRUD)
    path("companies/", AdminCompanyView.as_view(), name="companies"),
    path("companies/create/", AdminCompanyCreateView.as_view(), name="company_create"),
    path(
        "companies/<uuid:company_id>/edit/",
        AdminCompanyUpdateView.as_view(),
        name="company_edit",
    ),
    path(
        "companies/<uuid:company_id>/delete/",
        AdminCompanyDeleteView.as_view(),
        name="company_delete",
    ),

    # Autres sections
    path("coworking/", AdminCoworkingView.as_view(), name="coworking"),

    # CRUD Coworking - Categories
    path(
        "coworking/categories/create/",
        AdminCoworkingCategoryCreateView.as_view(),
        name="coworking_category_create",
    ),
    path(
        "coworking/categories/<int:category_id>/edit/",
        AdminCoworkingCategoryEditView.as_view(),
        name="coworking_category_edit",
    ),
    path(
        "coworking/categories/<int:category_id>/delete/",
        AdminCoworkingCategoryDeleteView.as_view(),
        name="coworking_category_delete",
    ),

    # CRUD Coworking - Equipements
    path(
        "coworking/equipments/create/",
        AdminCoworkingEquipmentCreateView.as_view(),
        name="coworking_equipment_create",
    ),
    path(
        "coworking/equipments/<int:equipment_id>/edit/",
        AdminCoworkingEquipmentEditView.as_view(),
        name="coworking_equipment_edit",
    ),
    path(
        "coworking/equipments/<int:equipment_id>/delete/",
        AdminCoworkingEquipmentDeleteView.as_view(),
        name="coworking_equipment_delete",
    ),

    # CRUD Coworking - Agences (CoworkingSpace)
    path(
        "coworking/spaces/create/",
        AdminCoworkingSpaceCreateView.as_view(),
        name="coworking_space_create",
    ),
    path(
        "coworking/spaces/<int:space_id>/edit/",
        AdminCoworkingSpaceEditView.as_view(),
        name="coworking_space_edit",
    ),
    path(
        "coworking/spaces/<int:space_id>/delete/",
        AdminCoworkingSpaceDeleteView.as_view(),
        name="coworking_space_delete",
    ),

    # CRUD Coworking - Workspaces
    path(
        "coworking/workspaces/create/",
        AdminCoworkingWorkspaceCreateView.as_view(),
        name="coworking_workspace_create",
    ),
    path(
        "coworking/workspaces/<int:workspace_id>/edit/",
        AdminCoworkingWorkspaceEditView.as_view(),
        name="coworking_workspace_edit",
    ),
    path(
        "coworking/workspaces/<int:workspace_id>/delete/",
        AdminCoworkingWorkspaceDeleteView.as_view(),
        name="coworking_workspace_delete",
    ),

    # CRUD Coworking - Galerie photos
    path(
        "coworking/workspace-images/add/",
        AdminCoworkingWorkspaceImageAddView.as_view(),
        name="coworking_workspaceimage_add",
    ),
    path(
        "coworking/workspace-images/<int:image_id>/delete/",
        AdminCoworkingWorkspaceImageDeleteView.as_view(),
        name="coworking_workspaceimage_delete",
    ),

    path("reservations/", AdminReservationsView.as_view(), name="reservations"),

    # Réservations (actions admin)
    path(
        "reservations/<uuid:reservation_id>/",
        AdminReservationDetailView.as_view(),
        name="reservation_detail",
    ),
    path(
        "reservations/<uuid:reservation_id>/edit/",
        AdminReservationEditView.as_view(),
        name="reservation_edit",
    ),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        AdminReservationCancelView.as_view(),
        name="reservation_cancel",
    ),
    path(
        "reservations/<uuid:reservation_id>/confirm/",
        AdminReservationConfirmView.as_view(),
        name="reservation_confirm",
    ),
    path(
        "reservations/<uuid:reservation_id>/refuse/",
        AdminReservationRefuseView.as_view(),
        name="reservation_refuse",
    ),



    # Back-office Formation (CRUD)
    path("formations/", AdminFormationDashboardView.as_view(), name="formations"),
    path("formations/list/", AdminFormationsListView.as_view(), name="formations_list"),
    path("formations/create/", AdminFormationCreateView.as_view(), name="formations_create"),
    path("formations/<int:formation_id>/edit/", AdminFormationEditView.as_view(), name="formations_edit"),
    path("formations/<int:formation_id>/delete/", AdminFormationDeleteView.as_view(), name="formations_delete"),

    # Back-office Sessions (CRUD)
    path("formations/sessions/", AdminSessionsListView.as_view(), name="sessions_list"),
    path("formations/sessions/create/", AdminSessionCreateView.as_view(), name="sessions_create"),
    path("formations/sessions/<int:session_id>/edit/", AdminSessionEditView.as_view(), name="sessions_edit"),
    path("formations/sessions/<int:session_id>/delete/", AdminSessionDeleteView.as_view(), name="sessions_delete"),

    path("formations/categories/", AdminFormationCategoryListView.as_view(), name="formations_category_list"),
    path("formations/categories/create/", AdminFormationCategoryCreateView.as_view(), name="formations_category_create"),
    path("formations/categories/<int:category_id>/edit/", AdminFormationCategoryEditView.as_view(), name="formations_category_edit"),
    path("formations/categories/<int:category_id>/delete/", AdminFormationCategoryDeleteView.as_view(), name="formations_category_delete"),

    # Back-office Formateurs (Trainer CRUD)
    path("formations/trainers/", AdminTrainersListView.as_view(), name="formations_trainers_list"),
    path("formations/trainers/create/", AdminTrainersCreateView.as_view(), name="formations_trainers_create"),
    path("formations/trainers/<int:trainer_id>/edit/", AdminTrainersEditView.as_view(), name="formations_trainers_edit"),
    path("formations/trainers/<int:trainer_id>/delete/", AdminTrainersDeleteView.as_view(), name="formations_trainers_delete"),
    path(
        "formations/trainers/<int:id>/",
        TrainerDetailView.as_view(),
        name="formations_trainers_detail",
    ),

    # Back-office Inscriptions (Devis/formation)
    path("formations/inscriptions/", AdminInscriptionsListView.as_view(), name="inscriptions_list"),
    path(
        "formations/inscriptions/<int:inscription_id>/valider/",
        AdminInscriptionValidateView.as_view(),
        name="inscription_validate",
    ),
    path(
        "formations/inscriptions/<int:inscription_id>/refuser/",
        AdminInscriptionRefuseView.as_view(),
        name="inscription_refuse",
    ),
    path(
        "formations/inscriptions/<int:inscription_id>/annuler/",
        AdminInscriptionCancelView.as_view(),
        name="inscription_cancel",
    ),
    path(
        "formations/<int:pk>/",
        views.FormationDetailView.as_view(),
        name="formations_detail",
    ),

    path("domiciliation/", AdminDomiciliationView.as_view(), name="domiciliation"),

    # CRUD Domiciliation - Demandes
    path("domiciliation/requests/", AdminDomiciliationRequestsListView.as_view(), name="domiciliation_requests"),
    path(
        "domiciliation/requests/<uuid:request_id>/edit/",
        AdminDomiciliationRequestEditView.as_view(),
        name="domiciliation_request_edit",
    ),
    path(
        "domiciliation/requests/<uuid:request_id>/validate/",
        AdminDomiciliationRequestValidateView.as_view(),
        name="domiciliation_request_validate",
    ),
    path(
        "domiciliation/requests/<uuid:request_id>/refuse/",
        AdminDomiciliationRequestRefuseView.as_view(),
        name="domiciliation_request_refuse",
    ),

    # CRUD Domiciliation - Formules

    path(
        "domiciliation/plans/",
        AdminDomiciliationPlansListView.as_view(),
        name="domiciliation_plans",
    ),
    path(
        "domiciliation/plans/create/",
        AdminDomiciliationPlanCreateView.as_view(),
        name="domiciliation_plans_create",
    ),
    path(
        "domiciliation/plans/<int:plan_id>/edit/",
        AdminDomiciliationPlanEditView.as_view(),
        name="domiciliation_plans_edit",
    ),
    path(
        "domiciliation/plans/<int:plan_id>/delete/",
        AdminDomiciliationPlanDeleteView.as_view(),
        name="domiciliation_plans_delete",
    ),
path(
        "domiciliation/<uuid:request_id>/",
        views.domiciliation_detail,
        name="domiciliation_detail"
    ),
    path(
        "domiciliation/<uuid:request_id>/contract/",
        views.domiciliation_contract_view,
        name="domiciliation_contract_view",
    ),
    path(
        "domiciliation/<uuid:request_id>/contract/send/",
        views.domiciliation_contract_send,
        name="domiciliation_contract_send",
    ),



    # Profils (consult/modify)

    path("profile/", AdminProfileView.as_view(), name="profile_view"),
    path(
        "profile/<uuid:user_id>/edit/",
        AdminProfileEditView.as_view(),
        name="profile_edit",
    ),

    # Avis Clients (Testimonials)
    path("testimonials/", AdminTestimonialListView.as_view(), name="testimonials_list"),
    path(
        "testimonials/<int:testimonial_id>/approve/",
        AdminTestimonialApproveView.as_view(),
        name="testimonial_approve",
    ),
    path(
        "testimonials/<int:testimonial_id>/reject/",
        AdminTestimonialRejectView.as_view(),
        name="testimonial_reject",
    ),

    # Demandes de devis formation
    path("devis-formation/", AdminDevisFormationListView.as_view(), name="devis_formation_list"),
    path(
        "devis-formation/<int:devis_id>/mark-read/",
        AdminDevisMarkReadView.as_view(),
        name="devis_formation_mark_read",
    ),
    path(
        "devis-formation/<int:devis_id>/mark-unread/",
        AdminDevisMarkUnreadView.as_view(),
        name="devis_formation_mark_unread",
    ),
    path(
        "devis/<int:pk>/envoyer/",
        send_devis_email,
        name="send_devis_email"
    ),

    # Messages de contact
    path("contact-messages/", AdminContactMessagesListView.as_view(), name="contact_messages"),
    path(
        "contact-messages/<int:message_id>/",
        AdminContactMessageDetailView.as_view(),
        name="contact_message_detail",
    ),
    path(
        "contact-messages/<int:message_id>/mark-read/",
        AdminContactMessageMarkReadView.as_view(),
        name="contact_message_mark_read",
    ),
    path(
        "contact-messages/<int:message_id>/mark-unread/",
        AdminContactMessageMarkUnreadView.as_view(),
        name="contact_message_mark_unread",
    ),
    path(
        "contact-messages/<int:message_id>/delete/",
        AdminContactMessageDeleteView.as_view(),
        name="contact_message_delete",
    ),

    # Paiements / Méthodes de paiement / Factures / Reçus (Admin back-office)
    path("payments/", AdminPaymentsListView.as_view(), name="payments"),
    path(
        "payments/reservations/<uuid:reservation_id>/",
        AdminPaymentsReservationView.as_view(),
        name="payment_reservation_detail",
    ),
    path(
        "payments/reservations/<uuid:reservation_id>/confirm/",
        AdminPaymentConfirmView.as_view(),
        name="payment_confirm",
    ),
    path(
        "payments/reservations/<uuid:reservation_id>/cancel/",
        AdminPaymentCancelView.as_view(),
        name="payment_cancel",
    ),
    path(
        "payments/reservations/<uuid:reservation_id>/refund/",
        AdminPaymentRefundView.as_view(),
        name="payment_refund",
    ),

    path(
        "payments/invoices/<uuid:invoice_id>/download/",
        AdminInvoicesDownloadView.as_view(),
        name="invoice_download",
    ),
    path(
        "payments/receipts/<uuid:receipt_id>/download/",
        AdminReceiptDownloadView.as_view(),
        name="receipt_download",
    ),

    # Demande de conciergerie
    path("conciergerie/", AdminConciergerieListView.as_view(), name="conciergerie_list"),
    path(
        "conciergerie/<int:demande_id>/",
        AdminConciergerieDetailView.as_view(),
        name="conciergerie_detail",
    ),
    path(
        "conciergerie/<int:demande_id>/validate/",
        AdminConciergerieValidateView.as_view(),
        name="conciergerie_validate",
    ),
    path(
        "conciergerie/<int:demande_id>/refuse/",
        AdminConciergerieRefuseView.as_view(),
        name="conciergerie_refuse",
    ),

    path(
        "payment-methods/",
        AdminPaymentMethodListView.as_view(),
        name="payment_methods",
    ),
    path(
        "payment-methods/create/",
        AdminPaymentMethodCreateView.as_view(),
        name="payment_methods_create",
    ),
    path(
        "payment-methods/<int:method_id>/edit/",
        AdminPaymentMethodEditView.as_view(),
        name="payment_methods_edit",
    ),
    path(
        "payment-methods/<int:method_id>/delete/",
        AdminPaymentMethodDeleteView.as_view(),
        name="payment_methods_delete",
    ),
]


# ───────────────────────────────────────────────
#  DASHBOARD FORMATEUR (TRAINER)
#  Included in config/urls.py as:
#  path('dashboard/trainer/', include((dashboard_trainer_urls, 'dashboard'), namespace='dashboard_trainer'))
# ───────────────────────────────────────────────
dashboard_trainer_urls = [
    path("", TrainerDashboardView.as_view(), name="index"),
    path("sessions/", TrainerSessionsView.as_view(), name="sessions"),
    path("sessions/create/", TrainerSessionCreateView.as_view(), name="session_create"),
    path("sessions/<int:session_id>/edit/", TrainerSessionEditView.as_view(), name="session_edit"),
    path("students/", TrainerStudentsView.as_view(), name="students"),
    path("students/<int:inscription_id>/detail/", TrainerStudentDetailView.as_view(), name="student_detail"),
    path("students/<int:inscription_id>/validate/", TrainerStudentValidateView.as_view(), name="student_validate"),
    path("students/<int:inscription_id>/refuse/", TrainerStudentRefuseView.as_view(), name="student_refuse"),
    path("revenue/", TrainerRevenueView.as_view(), name="revenue"),
    path("formations/", TrainerFormationsView.as_view(), name="formations"),
    path("documents/", TrainerDocumentsView.as_view(), name="documents"),
    path("reviews/", TrainerReviewsView.as_view(), name="reviews"),
    path("settings/", TrainerSettingsView.as_view(), name="settings"),
    path(
        "documents/add/",
        trainer_views.add_document,
        name="add_document"
    ),
    path(
        "formations/<int:pk>/",
        TrainerFormationDetailView.as_view(),
        name="formation_detail"
    ),
    path(
        "sessions/<int:session_id>/delete/",
        TrainerSessionDeleteView,
        name="session_delete"
    ),
    path(
        "documents/<int:document_id>/delete/",
        delete_document,
        name="delete_document"
    ),
    path(
        "devis-formation/",
        TrainerDevisFormationView.as_view(),
        name="devis_formation_list"
    ),
    path(
        "devis-formation/<int:pk>/",
        DevisFormationDetailView.as_view(),
        name="devis_formation_detail"
    ),
    path(
        "reservations/",
        TrainerReservationsView.as_view(),
        name="trainer_reservations"
    ),
    path(
        "reservations/create/",
        TrainerReservationCreateView.as_view(),
        name="trainer_reservation_create"
    ),
    path(
        "reservations/<uuid:reservation_id>/",
        TrainerReservationDetailView.as_view(),
        name="trainer_reservation_detail"
    ),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        TrainerReservationCancelView.as_view(),
        name="trainer_reservation_cancel"
    ),
    path(
        "devis/<int:devis_id>/pdf/",
        views.devis_formation_pdf,
        name="devis_formation_pdf"
    ),
     path(
        "devis/<int:pk>/send/",
        send_devis_email,
        name="send_devis_email"
    ),
]

