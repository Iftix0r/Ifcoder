package uz.ifcoder.operator.ui

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.Menu
import android.view.MenuItem
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import kotlinx.coroutines.launch
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.data.StatusUpdateRequest
import uz.ifcoder.operator.data.TaskDto
import uz.ifcoder.operator.location.LocationTrackingService

class TaskListActivity : AppCompatActivity() {

    private val permissionsHelper = PermissionsHelper(this)

    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var recyclerTasks: RecyclerView
    private lateinit var adapter: TaskAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_task_list)
        setSupportActionBar(findViewById<Toolbar>(R.id.toolbar))

        swipeRefresh = findViewById(R.id.swipeRefresh)
        recyclerTasks = findViewById(R.id.recyclerTasks)

        adapter = TaskAdapter(
            onMarkDone = { task -> markTaskDone(task) },
            onOpenDetail = { task -> TaskDetailActivity.start(this, task) },
        )
        recyclerTasks.layoutManager = LinearLayoutManager(this)
        recyclerTasks.adapter = adapter

        swipeRefresh.setOnRefreshListener { loadTasks() }
        loadTasks()
    }

    override fun onResume() {
        super.onResume()
        loadTasks()
        if (permissionsHelper.hasForegroundLocation()) {
            Log.d(TAG, "onResume: joylashuv ruxsati bor — xizmat (qayta) ishga tushirilmoqda")
            LocationTrackingService.start(this)
        } else {
            Log.w(TAG, "onResume: joylashuv ruxsati YO'Q — xizmat ishga tushmaydi")
        }
    }

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_task_list, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        when (item.itemId) {
            R.id.action_logout -> {
                logout()
                return true
            }
            R.id.action_refresh_permissions -> {
                refreshPermissions()
                return true
            }
        }
        return super.onOptionsItemSelected(item)
    }

    /** Foydalanuvchi menyudan qo'lda chaqirsa — barcha ruxsatlarni qayta so'raydi va
     * xizmatni qayta ishga tushiradi. Login paytida rad etilgan yoki keyinchalik
     * tizim tomonidan olib tashlangan ruxsatlarni logout qilmasdan tiklash uchun. */
    private fun refreshPermissions() {
        if (!permissionsHelper.hasForegroundLocation()) {
            permissionsHelper.requestForegroundLocation { granted ->
                if (granted) requestBackgroundThenRestart() else showPermissionDenied()
            }
        } else {
            requestBackgroundThenRestart()
        }
    }

    private fun requestBackgroundThenRestart() {
        if (!permissionsHelper.hasBackgroundLocation()) {
            permissionsHelper.requestBackgroundLocation { requestBatteryOptimizationThenRestart() }
        } else {
            requestBatteryOptimizationThenRestart()
        }
    }

    private fun requestBatteryOptimizationThenRestart() {
        permissionsHelper.requestIgnoreBatteryOptimizations { restartLocationServiceWithFeedback() }
    }

    private fun restartLocationServiceWithFeedback() {
        LocationTrackingService.start(this)
        Toast.makeText(
            this,
            getString(R.string.permissions_all_granted_hint, getString(R.string.app_name)),
            Toast.LENGTH_LONG,
        ).show()
    }

    private fun showPermissionDenied() {
        Toast.makeText(
            this,
            getString(R.string.permissions_denied_hint, getString(R.string.app_name)),
            Toast.LENGTH_LONG,
        ).show()
    }

    private fun loadTasks() {
        swipeRefresh.isRefreshing = true
        lifecycleScope.launch {
            try {
                val response = ApiClient.api().getTasks()
                if (response.isSuccessful) {
                    adapter.submitList(response.body().orEmpty())
                    findViewById<android.widget.TextView>(R.id.textEmpty).visibility =
                        if (response.body().isNullOrEmpty()) android.view.View.VISIBLE else android.view.View.GONE
                }
            } catch (e: Exception) {
                Toast.makeText(this@TaskListActivity, R.string.login_network_error, Toast.LENGTH_SHORT).show()
            } finally {
                swipeRefresh.isRefreshing = false
            }
        }
    }

    private fun markTaskDone(task: TaskDto) {
        lifecycleScope.launch {
            try {
                ApiClient.api().updateTaskStatus(task.id, StatusUpdateRequest(status = "done"))
                loadTasks()
            } catch (e: Exception) {
                Toast.makeText(this@TaskListActivity, R.string.login_network_error, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun logout() {
        LocationTrackingService.stop(this)
        ApiClient.tokens().clear()
        startActivity(Intent(this, LoginActivity::class.java))
        finish()
    }

    companion object {
        private const val TAG = "TaskListActivity"
    }
}
