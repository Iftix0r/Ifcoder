package uz.ifcoder.operator.data

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {

    @POST("login/")
    suspend fun login(@Body body: LoginRequest): Response<LoginResponse>

    @GET("tasks/")
    suspend fun getTasks(): Response<List<TaskDto>>

    @POST("tasks/{id}/status/")
    suspend fun updateTaskStatus(
        @Path("id") taskId: Int,
        @Body body: StatusUpdateRequest,
    ): Response<StatusUpdateResponse>

    @POST("location/")
    suspend fun postLocation(@Body body: LocationPingRequest): Response<Unit>

    @POST("device-token/")
    suspend fun registerDeviceToken(@Body body: DeviceTokenRequest): Response<Unit>
}
