package uz.ifcoder.operator.ui

import android.content.Intent
import android.os.Bundle
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

    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var recyclerTasks: RecyclerView
    private lateinit var adapter: TaskAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_task_list)
        setSupportActionBar(findViewById<Toolbar>(R.id.toolbar))

        swipeRefresh = findViewById(R.id.swipeRefresh)
        recyclerTasks = findViewById(R.id.recyclerTasks)

        adapter = TaskAdapter(onMarkDone = { task -> markTaskDone(task) })
        recyclerTasks.layoutManager = LinearLayoutManager(this)
        recyclerTasks.adapter = adapter

        swipeRefresh.setOnRefreshListener { loadTasks() }
        loadTasks()
    }

    override fun onResume() {
        super.onResume()
        loadTasks()
        if (hasLocationPermission()) {
            LocationTrackingService.start(this)
        }
    }

    private fun hasLocationPermission(): Boolean =
        androidx.core.content.ContextCompat.checkSelfPermission(
            this, android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == android.content.pm.PackageManager.PERMISSION_GRANTED

    override fun onCreateOptionsMenu(menu: Menu): Boolean {
        menuInflater.inflate(R.menu.menu_task_list, menu)
        return true
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        if (item.itemId == R.id.action_logout) {
            logout()
            return true
        }
        return super.onOptionsItemSelected(item)
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
}
