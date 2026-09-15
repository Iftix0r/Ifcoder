package uz.ifcoder.operator.ui

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import uz.ifcoder.operator.R
import uz.ifcoder.operator.data.TaskDto

class TaskAdapter(
    private val onMarkDone: (TaskDto) -> Unit,
) : RecyclerView.Adapter<TaskAdapter.TaskViewHolder>() {

    private val tasks = mutableListOf<TaskDto>()

    fun submitList(newTasks: List<TaskDto>) {
        tasks.clear()
        tasks.addAll(newTasks)
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, position: Int): TaskViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.row_task, parent, false)
        return TaskViewHolder(view)
    }

    override fun onBindViewHolder(holder: TaskViewHolder, position: Int) {
        holder.bind(tasks[position], onMarkDone)
    }

    override fun getItemCount(): Int = tasks.size

    class TaskViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val title: TextView = itemView.findViewById(R.id.textTaskTitle)
        private val client: TextView = itemView.findViewById(R.id.textTaskClient)
        private val status: TextView = itemView.findViewById(R.id.textTaskStatus)
        private val markDone: Button = itemView.findViewById(R.id.buttonMarkDone)

        fun bind(task: TaskDto, onMarkDone: (TaskDto) -> Unit) {
            title.text = task.title
            client.text = if (task.client_name.isNotBlank()) {
                "${task.client_name} · ${task.client_phone}"
            } else {
                itemView.context.getString(R.string.tasks_no_client)
            }
            status.text = task.status_label
            markDone.visibility = if (task.status == "done") View.GONE else View.VISIBLE
            markDone.setOnClickListener { onMarkDone(task) }
        }
    }
}
