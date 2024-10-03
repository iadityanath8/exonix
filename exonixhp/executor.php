<?php


function sleep_float($seconds)
{
    if ($seconds >= 1) {
        $whole_seconds = floor($seconds);
        $fractional_seconds = $seconds - $whole_seconds;
    } else {
        $whole_seconds = 0;
        $fractional_seconds = $seconds;
    }

    if ($whole_seconds > 0) {
        sleep($whole_seconds);
    }

    if ($fractional_seconds > 0) {
        usleep($fractional_seconds * 1_000_000);
    }
}

enum Status
{
    case PENDING;
    case CANCELLED;
    case FINISHED;
}

class Future
{
    protected mixed        $result;
    protected TaskExecutor $sched;
    protected Status       $status;
    protected bool         $done;

    /****  This will be kind of slow due to cache misses we will soon use      * 
     * our custome ring buffer or an simple array till now it is fine i guess 
     */
    protected SplQueue     $callbacks;

    public function __construct($exe)
    {
        $this->sched     =  $exe;
        $this->status    =  Status::PENDING;
        $this->done      =  false;
        $this->callbacks =  new SplQueue();
    }

    public function set_result($res)
    {
        $this->result  = $res;
        $this->done    = true;
        $this->status  = Status::FINISHED;

        if (!$this->callbacks->isEmpty()) {
            $this->sched->call_soon($this->callbacks->dequeue());
        }
    }

    public function get_result()
    {
        if ($this->done == false or $this->status == Status::PENDING) {
            $this->callbacks->enqueue($this->sched->get_current());
            $this->sched->set_current(null);
            Fiber::suspend();
        }
        return $this->result;
    }
}

class Task extends Future
{
    private Fiber        $coro;

    public function __construct($coro, $exe)
    {
        parent::__construct($exe);
        $this->coro    =  $coro;
    }

    public function call()
    {
        if (!$this->coro->isStarted()) {
            $this->coro->start();
        } else {
            if ($this->coro->isTerminated()) {;
                $this->set_result($this->coro->getReturn());
                return;
            } else {
                $this->sched->set_current($this);
                $this->coro->resume();
            }
        }
        if ($this->sched->get_current() != null) {
            $this->sched->call_soon($this);
        }
    }
}

class TaskExecutor
{
    private SplQueue   $ready_tasks;
    private SplMinHeap $sleeping_tasks;
    private int        $id;
    private ?Task      $current;
    private mixed      $read_waiters;
    private mixed      $write_waiters;

    public function __construct()
    {
        $this->ready_tasks    =  new SplQueue();
        $this->sleeping_tasks =  new SplMinHeap();
        $this->id             =  0;
        $this->current        =  null;
        $this->read_waiters   = [];
        $this->write_waiters  = [];
    }

    public function call_soon($task)
    {
        if ($task instanceof Task) {
            $this->ready_tasks->enqueue($task);
        } else {
            $this->ready_tasks->enqueue(new Task(new Fiber($task), $this));
        }
    }

    public function sleep($delay)
    {
        $deadline = microtime(true) + $delay;
        $this->id++;
        $this->sleeping_tasks->insert([$deadline, $this->id, $this->current]);
        $this->current = null;
        Fiber::suspend();
    }

    public function read_wait($fileno, $task)
    {
        $this->read_waiters[socket_get_option($fileno,SOL_SOCKET,SO_TYPE)] = ['socket' => $fileno,'task' => $task];
    }

    public function write_wait($fileno, $task)
    {
        $this->write_waiters[socket_get_option($fileno,SOL_SOCKET,SO_TYPE)] = ['socket' => $fileno,'task' => $task];
    }

    public function get_current()
    {
        return $this->current;
    }
    public function set_current($val)
    {
        $this->current = $val;
    }
    public function run_loop()
    {
        while (
            !$this->ready_tasks->isEmpty() || !$this->sleeping_tasks->isEmpty()
            || count($this->read_waiters) > 0 || count($this->write_waiters) > 0
        ) {

            if ($this->ready_tasks->isEmpty()) {

                $timeout = 0;
                if (!$this->sleeping_tasks->isEmpty()) {
                    list($deadline, $id, $func) = $this->sleeping_tasks->top();
                    $timeout = $deadline - microtime(true);
                    if ($timeout < 0) {
                        $timeout = 0;
                    }
                } else {
                    $timeout = null;
                }

                $reader   = array_values($this->read_waiters);
                $writters = array_values($this->write_waiters);


                if (!empty($reader) || !empty($writters)) {
                    socket_select($reader, $writters, $except, $timeout);
                    // later handle the error's
                } else {
                    if ($timeout != null) {
                        usleep($timeout * 1000000);
                    }
                }

                foreach ($reader as $rfd) {
                    $this->call_soon($this->read_waiters[socket_get_option($rfd,SOL_SOCKET,SO_TYPE)]['tasks']);
                }

                foreach ($writters as $wfd) {
                    $this->call_soon($this->write_waiters[socket_get_option($wfd,SOL_SOCKET,SO_TYPE)]['tasks']);
                }

                $now = microtime(true);
                while (!$this->sleeping_tasks->isEmpty()) {
                    if ($now > $this->sleeping_tasks->top()[0]) {
                        $this->call_soon($this->sleeping_tasks->extract()[2]);
                    } else {
                        break;
                    }
                }
            }

            $this->current = $this->ready_tasks->dequeue();
            $this->current->call();
        }
    }
}



$sched = new TaskExecutor();

function recv($socket, $max_bytes)
{
    global $sched;
    $sched->read_wait($socket, $sched->get_current());
    $sched->set_current(null);
    Fiber::suspend();
    return socket_read($socket, 1024);
}

function send($socket, $data)
{
    global $sched;
    $sched->write_wait($socket, $sched->get_current());
    $sched->set_current(null);
    Fiber::suspend();
    return socket_write($socket, $data);
}

function accept($socket)
{
    global $sched;
    $sched->read_wait($socket, $sched->get_current());
    $sched->set_current(null);
    Fiber::suspend();
    return socket_accept($socket);
}



function main()
{
    global $sched;
    $server_sock = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
    if ($server_sock === false) {
        die("Failed to create socket: " . socket_strerror(socket_last_error()));
    }
    socket_set_option($server_sock, SOL_SOCKET, SO_REUSEADDR, 1);

    socket_bind($server_sock, '127.0.0.1', 8080);
    socket_listen($server_sock);

    echo "Server started\n";

    while (true) {
        $clientsock = accept($server_sock);
        if ($clientsock === false) {
            die("Failed to accept a client: " . socket_strerror(socket_last_error()));
        }
        echo "Client connected\n";
        $sched->call_soon(function () use($clientsock){
            handle_conn($clientsock);
        });
    }   

    socket_close($server_sock);
}

function handle_conn($clientsock)
{
    while (true) {
        $data = recv($clientsock, 1024);
        if ($data === false) {
            echo "Failed to read the data or client disconnected\n";
            break;  // Exit the loop if read fails or client disconnects
        } elseif (trim($data) === "") {
            echo "Client disconnected (no data)\n";
            break;  // Handle empty data read as a disconnection
        } else {
            $response = "GOT " . trim($data);
            send($clientsock, $response);
        }
    }

    socket_close($clientsock);
    echo "Closing the client socket\n";
}

$sched->call_soon('main');
$sched->run_loop();

?>