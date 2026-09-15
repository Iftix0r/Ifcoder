package uz.ifcoder.operator.ui

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.View
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.ApiClient
import uz.ifcoder.operator.data.StatusUpdateRequest
import uz.ifcoder.operator.data.TaskDto
import uz.ifcoder.operator.push.SmsHelper

class TaskDetailActivity : AppCompatActivity() {

    private val permissionsHelper = PermissionsHelper(this)

    private lateinit var task: TaskDto

    private lateinit var textStatus: TextView
    private lateinit var buttonStatus: android.widget.Button
    private lateinit var buttonCall: android.widget.Button
    private lateinit var buttonSms: android.widget.Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_task_detail)
        setSupportActionBar(findViewById<Toolbar>(R.id.toolbar))
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        @Suppress("DEPRECATION")
        task = intent.getSerializableExtra(EXTRA_TASK) as? TaskDto
            ?: run { finish(); return }

        findViewById<TextView>(R.id.textTitle).text = task.title
        findViewById<TextView>(R.id.textDescription).text =
            task.description.ifBlank { getString(R.string.task_detail_no_description) }
        findViewById<TextView>(R.id.textClient).text =
            task.client_name.ifBlank { getString(R.string.tasks_no_client) }
        findViewById<TextView>(R.id.textProject).text = task.project_name.ifBlank { "—" }
        findViewById<TextView>(R.id.textDue).text = task.due_date ?: "—"
        findViewById<TextView>(R.id.textPriority).text = task.priority_label

        textStatus = findViewById(R.id.textStatus)
        buttonStatus = findViewById(R.id.buttonStatus)
        buttonCall = findViewById(R.id.buttonCall)
        buttonSms = findViewById(R.id.buttonSms)

        renderStatus()

        buttonCall.setOnClickListener { callClient() }
        buttonSms.setOnClickListener { promptSms() }
        buttonStatus.setOnClickListener { advanceStatus() }
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun renderStatus() {
        textStatus.text = task.status_label
        when (task.status) {
            "todo" -> {
                buttonStatus.text = getString(R.string.task_action_start)
                buttonStatus.visibility = View.VISIBLE
            }
            "in_progress" -> {
                buttonStatus.text = getString(R.string.task_action_done)
                buttonStatus.visibility = View.VISIBLE
            }
            else -> buttonStatus.visibility = View.GONE
        }
    }

    private fun advanceStatus() {
        val nextStatus = when (task.status) {
            "todo" -> "in_progress"
            "in_progress" -> "done"
            else -> return
        }
        lifecycleScope.launch {
            try {
                val response = ApiClient.api().updateTaskStatus(task.id, StatusUpdateRequest(nextStatus))
                if (response.isSuccessful) {
                    task = task.copy(status = nextStatus, status_label = statusLabelFor(nextStatus))
                    renderStatus()
                } else {
                    Toast.makeText(this@TaskDetailActivity, R.string.task_update_failed, Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@TaskDetailActivity, R.string.login_network_error, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun statusLabelFor(status: String): String = when (status) {
        "todo" -> getString(R.string.task_status_todo)
        "in_progress" -> getString(R.string.task_status_in_progress)
        "done" -> getString(R.string.task_status_done)
        else -> status
    }

    private fun callClient() {
        if (task.client_phone.isBlank()) {
            Toast.makeText(this, R.string.task_no_phone, Toast.LENGTH_SHORT).show()
            return
        }
        startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${task.client_phone}")))
    }

    private fun promptSms() {
        if (task.client_phone.isBlank()) {
            Toast.makeText(this, R.string.task_no_phone, Toast.LENGTH_SHORT).show()
            return
        }
        if (!permissionsHelper.hasSms()) {
            permissionsHelper.requestSms { granted -> if (granted) showSmsDialog() }
            return
        }
        showSmsDialog()
    }

    private fun showSmsDialog() {
        val input = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
            setText(getString(R.string.sms_default_text, task.client_name, task.title))
            setSelection(text.length)
        }
        AlertDialog.Builder(this)
            .setTitle(R.string.sms_dialog_title)
            .setView(input)
            .setPositiveButton(R.string.sms_dialog_send) { _, _ ->
                val sent = SmsHelper.sendSms(this, task.client_phone, input.text.toString())
                val messageRes = if (sent) R.string.sms_sent_title else R.string.sms_failed_title
                Toast.makeText(this, messageRes, Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton(R.string.sms_dialog_cancel, null)
            .show()
    }

    companion object {
        private const val EXTRA_TASK = "extra_task"

        fun start(context: android.content.Context, task: TaskDto) {
            context.startActivity(
                Intent(context, TaskDetailActivity::class.java).putExtra(EXTRA_TASK, task)
            )
        }
    }
}
