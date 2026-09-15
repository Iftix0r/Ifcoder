package uz.ifcoder.operator.data

import java.io.Serializable

data class LoginRequest(
    val username: String,
    val password: String,
)

data class LoginResponse(
    val token: String,
)

data class StatusUpdateRequest(
    val status: String,
)

data class TaskDto(
    val id: Int,
    val title: String,
    val description: String,
    val status: String,
    val status_label: String,
    val priority: String,
    val priority_label: String,
    val due_date: String?,
    val client_name: String,
    val client_phone: String,
    val project_name: String,
) : Serializable

data class StatusUpdateResponse(
    val ok: Boolean,
    val status: String?,
)

data class LocationPingRequest(
    val latitude: Double,
    val longitude: Double,
    val accuracy: Float?,
    val recorded_at: String,
)

data class DeviceTokenRequest(
    val fcm_token: String,
    val device_id: String,
)
